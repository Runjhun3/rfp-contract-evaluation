"""The only way code talks to the LLM.

- Every response is cached on disk (key = model + system + user + page images), so re-runs cost
  nothing and a run can be replayed without AWS (LLM_MODE=replay).
- Every response is parsed into a Pydantic model. A model that corrects itself mid-answer
  may write an object, a note, then the corrected object: the last object that fits wins.
- An unusable response gets one retry with the error appended, then fails. A failed ask
  leaves nothing in the cache, so a re-run asks again instead of replaying the failure.
"""
import hashlib
import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings

M = TypeVar("M", bound=BaseModel)
Completer = Callable[[str, str, list[bytes]], str]


class ReplayMiss(RuntimeError):
    pass


def json_objects(text: str) -> list[dict]:
    """Every complete top-level JSON object in a response, in order. Text around and
    between them (code fences, notes) is skipped."""
    decoder = json.JSONDecoder()
    found, at = [], text.find("{")
    while at >= 0:
        try:
            value, end = decoder.raw_decode(text, at)
        except json.JSONDecodeError:
            at = text.find("{", at + 1)
            continue
        if isinstance(value, dict):
            found.append(value)
        at = text.find("{", end)
    return found


def parse(text: str, model: type[M]) -> M:
    """The last object in the response that fits the model: a correction comes after the
    answer it corrects."""
    objects = json_objects(text)
    if not objects:
        raise ValueError("no JSON object in response")
    first_error = None
    for value in reversed(objects):
        try:
            return model.model_validate(value)
        except ValidationError as err:
            first_error = first_error or err
    raise first_error


class LlmClient:
    def __init__(self, settings: Settings, completer: Completer | None = None):
        self.settings = settings
        self.cache_dir = Path(settings.llm_cache_dir)
        self.completer = completer

    def ask_json(self, system: str, user: str, model: type[M],
                 images: list[bytes] | None = None) -> M:
        """images: PNG page images sent before the text (e.g. CV tables whose text layer
        is out of reading order)."""
        try:
            return parse(self.complete(system, user, images), model)
        except ValueError as err:
            retry = (f"{user}\n\nYour previous answer could not be used: {err}\n"
                     "Start again from the source text. Return one complete, valid JSON object "
                     "only; do not repeat the previous answer.")
        try:
            return parse(self.complete(system, retry, images), model)
        except ValueError:
            self.forget(system, user, images)
            self.forget(system, retry, images)
            raise

    def complete(self, system: str, user: str, images: list[bytes] | None = None) -> str:
        images = images or []
        path = self._cache_path(system, user, images)
        if path.exists():
            return path.read_text(encoding="utf-8")
        if self.settings.llm_mode == "replay":
            raise ReplayMiss(f"no cached response {path.name}")
        text = self._completer()(system, user, images)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text

    def forget(self, system: str, user: str, images: list[bytes] | None = None) -> None:
        """Drop a cached response that could not be used. Replay mode keeps its recordings."""
        if self.settings.llm_mode != "replay":
            self._cache_path(system, user, images or []).unlink(missing_ok=True)

    def _cache_path(self, system: str, user: str, images: list[bytes]) -> Path:
        raw = f"{self.settings.claude_model}\x00{system}\x00{user}".encode()
        for image in images:   # no images -> same key as before, old cache entries stay valid
            raw += b"\x00" + hashlib.sha256(image).digest()
        return self.cache_dir / f"{hashlib.sha256(raw).hexdigest()}.txt"

    def _completer(self) -> Completer:
        if self.completer is None:
            from app.llm.bedrock import make_completer
            self.completer = make_completer(self.settings)
        return self.completer

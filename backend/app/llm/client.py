"""The only way code talks to the LLM.

- Every response is cached on disk (key = model + system + user + page images), so re-runs cost
  nothing and a run can be replayed without AWS (LLM_MODE=replay).
- Every response is parsed into a Pydantic model; invalid JSON gets one retry
  with the error appended, then fails.
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


def extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


class LlmClient:
    def __init__(self, settings: Settings, completer: Completer | None = None):
        self.settings = settings
        self.cache_dir = Path(settings.llm_cache_dir)
        self.completer = completer

    def ask_json(self, system: str, user: str, model: type[M],
                 images: list[bytes] | None = None) -> M:
        """images: PNG page images sent before the text (e.g. CV tables whose text layer
        is out of reading order)."""
        text = self.complete(system, user, images)
        try:
            return model.model_validate(extract_json(text))
        except (ValueError, ValidationError) as err:
            retry = (f"{user}\n\nYour previous answer could not be used: {err}\n"
                     f"Previous answer:\n{text}\nReturn corrected JSON only.")
            return model.model_validate(extract_json(self.complete(system, retry, images)))

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

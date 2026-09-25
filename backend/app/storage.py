"""Run folder I/O. Phase 1 keeps every step's output as JSON in one folder per
run (same shapes as docs/schema.md); Postgres replaces this in phase 2.
A step whose file exists is skipped, so an interrupted run resumes.
"""
import hashlib
import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T")


def cached(path: Path, kind: type[T], build: Callable[[], T]) -> T:
    adapter = TypeAdapter(kind)
    if path.exists():
        return adapter.validate_json(path.read_bytes())
    value = build()
    write(path, adapter.dump_python(value, mode="json"))
    return value


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_plain(data), indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_name(label: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-." else "_" for ch in label)


def _plain(data: object) -> object:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_plain(x) for x in data]
    return data

"""Render one bid page as PNG for the evidence viewer, cached on disk."""
from pathlib import Path

from app import files
from app.config import Settings
from app.ingest.page_render import render_pngs


def page_png(settings: Settings, key: str, page_no: int) -> bytes | None:
    cache = Path(settings.runs_dir) / "_page_cache" / key.replace("/", "_") / f"{page_no}.png"
    if cache.exists():
        return cache.read_bytes()
    png = render_pngs(files.local_path(settings, key), [page_no]).get(page_no)
    if png is None:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(png)
    return png

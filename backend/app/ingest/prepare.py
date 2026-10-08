"""A bid's pages, read, OCR'd where needed and labelled: the start of the evaluation
pipeline, eligibility screening and the document checks. Each step writes JSON and is
skipped when it is already there. Reading and OCR depend only on the bid file, so they
are kept once per file (pages_dir, see file_pages_dir) and every job reuses them: a
file is OCR'd once. Labels depend on the criteria and go into work_dir; the label
calls are also answered from the LLM reply cache when asked before.
"""
from pathlib import Path
from typing import Callable

from app.config import Settings
from app.ingest.label_pages import label_pages
from app.ingest.ocr import ocr_pages
from app.ingest.read_pages import read_pages
from app.llm.client import LlmClient
from app.schemas.records import Criterion, Page, Requirement
from app.storage import cached, safe_name

Stage = Callable[..., None]   # stage(name, done=0, total=0)


def file_pages_dir(settings: Settings, file_id: str) -> Path:
    """Where a bid file's read and OCR'd pages are kept, shared by every job."""
    return Path(settings.runs_dir) / "files" / file_id


def read_pages_once(bid_pdf: Path, bidder: str, pages_dir: Path, settings: Settings,
                    stage: Stage) -> list[Page]:
    """The file's pages with their text layer and OCR, read and OCR'd once per file."""
    stage("READING")
    pages = cached(pages_dir / "pages_text.json", list[Page], lambda: read_pages(bid_pdf))
    stage("OCR")
    return cached(pages_dir / "pages_ocr.json", list[Page],
                  lambda: ocr_pages(bid_pdf, pages, settings, safe_name(bidder)))


def labelled_pages(bid_pdf: Path, bidder: str, criteria: list[Criterion],
                   requirements: list[Requirement], work_dir: Path, settings: Settings,
                   llm: LlmClient, stage: Stage, pages_dir: Path | None = None) -> list[Page]:
    """pages_dir: the file's shared read and OCR (file_pages_dir); work_dir if none."""
    pages = read_pages_once(bid_pdf, bidder, pages_dir or work_dir, settings, stage)
    stage("LABELLING")
    return cached(work_dir / "pages_labelled.json", list[Page],
                  lambda: label_pages(pages, criteria, llm, requirements))

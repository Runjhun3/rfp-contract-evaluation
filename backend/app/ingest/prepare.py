"""A bid's pages, read, OCR'd where needed and labelled: the start of both the
evaluation pipeline and eligibility screening. Each step writes JSON into work_dir and
is skipped when it is already there; the label calls are also answered from the LLM
reply cache when the same bid was labelled with the same criteria before.
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


def labelled_pages(bid_pdf: Path, bidder: str, criteria: list[Criterion],
                   requirements: list[Requirement], work_dir: Path, settings: Settings,
                   llm: LlmClient, stage: Stage) -> list[Page]:
    stage("READING")
    pages = cached(work_dir / "pages_text.json", list[Page], lambda: read_pages(bid_pdf))
    stage("OCR")
    pages = cached(work_dir / "pages_ocr.json", list[Page],
                   lambda: ocr_pages(bid_pdf, pages, settings, safe_name(bidder)))
    stage("LABELLING")
    return cached(work_dir / "pages_labelled.json", list[Page],
                  lambda: label_pages(pages, criteria, llm, requirements))

"""Calibration (D-058, D-059): the document checks an evaluation would make, run on a bid
already evaluated, to see what they flag on genuine bids before FORENSIC_FLAGS shows
forensic findings to the committee. Reads the run's own pages and item results: no OCR
and no AI. Only each item's evidence pages are checked, as in an evaluation.

A run made before scan resolution and OCR word boxes were kept gets the resolution from
the PDF (free); its scans have no word boxes, so the checks needing them cannot run on
it, and the summary says so (they are never re-OCR'd here).

Writes <out>/report.csv (item, page, kind, score, note, crop), the crops and the bid's
index, and returns a summary.
"""
import csv
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from app.config import Settings
from app.evaluate.document_checks import cited_pages
from app.forensics.checker import DocumentChecker
from app.forensics.crops import save_crops
from app.ingest.read_pages import read_pages
from app.schemas.llm import ItemResult
from app.schemas.records import Item, Page
from app.storage import safe_name


def calibrate(settings: Settings, bid: Path, run_dir: Path, out: Path) -> str:
    """run_dir: an evaluation's folder for this bid (runs/<run>/<submission>)."""
    pages = _pages(bid, run_dir)
    cites = _cites(run_dir)
    evidence = {n for cited in cites.values() for n in cited}
    checker = DocumentChecker(bid, {p.pdf_page_no: p for p in pages}, settings, out,
                              sorted(evidence))
    rows = []
    try:
        for label, cited in cites.items():
            found = checker.forensic(cited)
            save_crops(checker.pdf, [f for f in found if not f.crop], out / "crops")
            rows += [(label, f.page, f.kind, round(f.score, 2), f.note, f.crop)
                     for f in found]
            rows += [(label, f.pages[0], f.kind, "", f.note, "")
                     for f in checker.identifiers(cited) if f.ok is False]
    finally:
        checker.close()
    _report(out / "report.csv", rows)
    kinds = Counter(r[2] for r in rows)
    boxes = "" if any(p.ocr_words for p in pages) else (
        " [no OCR word boxes in this run: near copy, letterhead and scanned word positions "
        "not checked]")
    return (f"{bid.name}: {len(rows)} flags on {len({r[1] for r in rows})} of {len(evidence)} "
            f"evidence pages ({len(pages)} in the bid) {dict(kinds)}{boxes} -> "
            f"{out / 'report.csv'}")


def _cites(run_dir: Path) -> dict[str, list[int]]:
    """Each evaluated item's evidence pages, as the evaluation checked them."""
    items = TypeAdapter(list[Item]).validate_json((run_dir / "items.json").read_bytes())
    found = {}
    for item in items:
        path = run_dir / "items" / f"{safe_name(item.label)}.json"
        if path.exists():
            found[item.label] = cited_pages(ItemResult.model_validate_json(path.read_bytes()),
                                            item)
    return found


def _pages(bid: Path, run_dir: Path) -> list[Page]:
    pages = TypeAdapter(list[Page]).validate_json((run_dir / "pages_labelled.json").read_bytes())
    if all(p.image_dpi is None for p in pages):           # read before it was kept
        dpi = {p.pdf_page_no: p.image_dpi for p in read_pages(bid)}
        pages = [p.model_copy(update={"image_dpi": dpi.get(p.pdf_page_no)}) for p in pages]
    return pages


def _report(path: Path, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item", "page", "kind", "score", "note", "crop"])
        writer.writerows(rows)

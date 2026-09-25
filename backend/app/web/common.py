"""Shared bits for API route modules: JSON replies, the project stepper, uploads."""
import hashlib
import io
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pypdfium2 as pdfium
from starlette.responses import JSONResponse

MAX_UPLOAD_BYTES = 150 * 1024 * 1024

STEPS = [("rfp", "Details & RFP"), ("criteria", "Criteria"),
         ("participants", "Participants & bids"), ("evaluate", "Evaluate"),
         ("results", "Results & review")]
STATUS_STEP = {"DRAFT": 0, "RFP_UPLOADED": 1, "CRITERIA_READY": 1, "PROMPT_APPROVED": 2,
               "EVALUATING": 3, "REVIEW": 4, "CLOSED": 4}


def format_marks(value) -> str:
    """12.00 -> 12, 9.50 -> 9.5. Marks go to the browser as exact strings, never floats."""
    text = f"{Decimal(str(value)):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _plain(value):
    if isinstance(value, Decimal):
        return format_marks(value)
    if isinstance(value, (UUID, date, datetime)):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


class ApiResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, default=_plain, ensure_ascii=False).encode("utf-8")


def ok(data, message: str = "ok", status_code: int = 200) -> ApiResponse:
    return ApiResponse({"data": data, "message": message}, status_code=status_code)


def fail(message: str, status_code: int = 400) -> ApiResponse:
    return ApiResponse({"data": None, "message": message}, status_code=status_code)


def stepper(project: dict, current: str, run_id: str | None) -> list[dict]:
    """Steps of one project; `url` is the React route, None while a step is locked."""
    reached = STATUS_STEP.get(project["status"], 0)
    base = f"/projects/{project['tender_id']}"
    urls = {"rfp": f"{base}/rfp", "criteria": f"{base}/criteria",
            "participants": f"{base}/participants",
            "evaluate": f"/runs/{run_id}" if run_id else None,
            "results": f"/runs/{run_id}/results" if run_id else None}
    return [{"n": i + 1, "key": key, "label": label, "url": urls[key] if i <= reached else None,
             "done": i < reached, "current": key == current}
            for i, (key, label) in enumerate(STEPS)]


class BadUpload(ValueError):
    pass


async def read_pdf_upload(form) -> tuple[str, bytes, str, int]:
    """Returns (file name, bytes, sha256, page count) or raises BadUpload."""
    upload = form.get("file")
    if upload is None or not getattr(upload, "filename", ""):
        raise BadUpload("Choose a PDF file first.")
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise BadUpload("The file is larger than 150 MB.")
    if not data.startswith(b"%PDF"):
        raise BadUpload("That file is not a PDF.")
    try:
        pages = len(pdfium.PdfDocument(io.BytesIO(data)))
    except pdfium.PdfiumError as err:
        raise BadUpload("The PDF could not be opened.") from err
    name = Path(upload.filename).name[:200]
    return name, data, hashlib.sha256(data).hexdigest(), pages

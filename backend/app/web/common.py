"""Shared bits for route modules: templates, rendering, the project stepper, uploads."""
import hashlib
import io
from decimal import Decimal
from pathlib import Path

import pypdfium2 as pdfium
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def format_marks(value) -> str:
    """12.00 -> 12, 9.50 -> 9.5, None -> —"""
    if value is None:
        return "—"
    text = f"{Decimal(str(value)):.2f}".rstrip("0").rstrip(".")
    return text or "0"


templates.env.filters["marks"] = format_marks
MAX_UPLOAD_BYTES = 150 * 1024 * 1024

STEPS = [("rfp", "Details & RFP"), ("criteria", "Criteria"),
         ("participants", "Participants & bids"), ("evaluate", "Evaluate"),
         ("results", "Results & review")]
STATUS_STEP = {"DRAFT": 0, "RFP_UPLOADED": 1, "CRITERIA_READY": 1, "PROMPT_APPROVED": 2,
               "EVALUATING": 3, "REVIEW": 4, "CLOSED": 4}


def render(request, name: str, user: dict, **context):
    context.update(request=request, user=user, csrf=request.session.get("csrf", ""))
    return templates.TemplateResponse(request, name, context)


def go(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def stepper(project: dict, current: str, run_id: str | None) -> list[dict]:
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

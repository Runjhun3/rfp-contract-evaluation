"""Textract OCR for selected pages of a PDF.

Only the pages that need OCR are copied into one small PDF, uploaded to
s3://<bucket>/tmp/<key>/ocr.pdf, read with async StartDocumentTextDetection,
then the tmp object is deleted.
"""
import io
import time
from pathlib import Path

import pypdfium2 as pdfium

from app.aws.clients import client
from app.config import Settings

POLL_SECONDS = 10
TIMEOUT_SECONDS = 30 * 60


def textract_pages(pdf_path: Path, page_nos: list[int], settings: Settings,
                   key: str) -> dict[int, tuple[str, float | None]]:
    s3, textract = client("s3", settings), client("textract", settings)
    object_key = f"tmp/{key}/ocr.pdf"
    s3.put_object(Bucket=settings.s3_bucket, Key=object_key, Body=_bundle(pdf_path, page_nos))
    try:
        job = textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": settings.s3_bucket, "Name": object_key}})
        lines = _collect_lines(textract, job["JobId"])
    finally:
        s3.delete_object(Bucket=settings.s3_bucket, Key=object_key)
    return {page_nos[i - 1]: _join(lines.get(i, [])) for i in range(1, len(page_nos) + 1)}


def _bundle(pdf_path: Path, page_nos: list[int]) -> bytes:
    source, bundle = pdfium.PdfDocument(str(pdf_path)), pdfium.PdfDocument.new()
    try:
        bundle.import_pages(source, [n - 1 for n in page_nos])
        buffer = io.BytesIO()
        bundle.save(buffer)
        return buffer.getvalue()
    finally:
        bundle.close()
        source.close()


def _collect_lines(textract, job_id: str) -> dict[int, list[tuple[str, float]]]:
    deadline, token, lines = time.time() + TIMEOUT_SECONDS, None, {}
    while True:
        args = {"JobId": job_id, **({"NextToken": token} if token else {})}
        result = textract.get_document_text_detection(**args)
        if result["JobStatus"] == "IN_PROGRESS":
            if time.time() > deadline:
                raise TimeoutError(f"Textract job {job_id} still running")
            time.sleep(POLL_SECONDS)
            continue
        if result["JobStatus"] != "SUCCEEDED":
            raise RuntimeError(f"Textract job {job_id}: {result['JobStatus']}")
        for block in result["Blocks"]:
            if block["BlockType"] == "LINE":
                lines.setdefault(block["Page"], []).append((block["Text"], block["Confidence"]))
        token = result.get("NextToken")
        if not token:
            return lines


def _join(lines: list[tuple[str, float]]) -> tuple[str, float | None]:
    if not lines:
        return "", None
    confidence = sum(c for _, c in lines) / len(lines) / 100
    return "\n".join(text for text, _ in lines), round(confidence, 3)

"""Python re-adds a CV's employment rows and compares the total with the years of
experience the LLM used. Both the first and the last month of a job count (Dec 2020 to
Nov 2023 is 36 months), as a CV means them; overlapping jobs count once; "present"
means the bid submission date. A difference of a year or more is a failed check (-> review).
Nothing is corrected.
"""
import re
from datetime import date
from decimal import Decimal

from app.schemas.llm import ItemResult, Job
from app.schemas.records import EvidenceCheck, Item

TOLERANCE_YEARS = Decimal("1")
_YEAR_MONTH = re.compile(r"^(\d{4})[-/.](\d{1,2})$")
_MONTH_YEAR = re.compile(r"^(\d{1,2})[-/.](\d{4})$")


def experience_check(result: ItemResult, item: Item, as_of: date) -> EvidenceCheck | None:
    cv = result.cv
    if cv is None or not cv.employment:
        return None
    months, unread = total_months(cv.employment, as_of)
    if unread == len(cv.employment):     # e.g. a one-page profile: nothing to add up
        return EvidenceCheck(label=item.label, fact="experience_years",
                             pdf_page_no=cv.employment[0].page, quote_found=True,
                             note="no employment row has readable dates; not recomputed")
    years = (Decimal(months) / 12).quantize(Decimal("0.1"))
    note = (f"{len(cv.employment) - unread} employment rows add up to {years} years "
            "(overlaps counted once)")
    if unread:
        note += f"; {unread} rows without readable dates"
    matches = None
    if cv.experience_years is not None:
        matches = abs(cv.experience_years - years) < TOLERANCE_YEARS
        if not matches:
            note += f"; the evaluation used {cv.experience_years} years"
    return EvidenceCheck(label=item.label, fact="experience_years",
                         pdf_page_no=cv.employment[0].page, quote_found=True, match_score=100,
                         parsed_value=str(years), value_matches=matches, note=note)


def total_months(jobs: list[Job], as_of: date) -> tuple[int, int]:
    """(months covered by the jobs, rows whose dates could not be read). A span runs
    from its start month up to, but not including, the month after its end month."""
    spans, unread = [], 0
    for job in jobs:
        start, end = _month(job.start, as_of), _month(job.end, as_of)
        if start is None or end is None or end < start:
            unread += 1
            continue
        spans.append((start, end + 1))  # the end month is worked too
    months, reach = 0, None
    for start, end in sorted(spans):
        if reach is not None and start < reach:
            start = reach                   # overlap with an earlier job: count once
        if end > start:
            months += end - start
        reach = end if reach is None else max(reach, end)
    return months, unread


def _month(text: str | None, as_of: date) -> int | None:
    """Month index (year * 12 + month - 1) of "YYYY-MM", "MM/YYYY" or "present"."""
    value = (text or "").strip().lower()
    if value == "present":
        return as_of.year * 12 + as_of.month - 1
    if match := _YEAR_MONTH.match(value):
        year, month = int(match.group(1)), int(match.group(2))
    elif match := _MONTH_YEAR.match(value):
        month, year = int(match.group(1)), int(match.group(2))
    else:
        return None
    return year * 12 + month - 1 if 1 <= month <= 12 else None

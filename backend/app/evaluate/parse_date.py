"""Read dates out of a quote, day-first (Indian format), never month-first.

A month-only date ("Dec 2021") matches a fact at month precision.
"""
import re
from datetime import date

from dateutil import parser

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_FULL = [
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th|[\"”'’`])?\s*(?:of\s+)?{MONTHS},?\s*\d{{4}}\b", re.I),
    re.compile(rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{4}}\b", re.I),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
]
_MONTH_ONLY = re.compile(rf"\b{MONTHS}\s*[',]?\s*(\d{{4}}|\d{{2}})\b", re.I)


def parse_dates(quote: str) -> tuple[list[date], list[tuple[int, int]]]:
    """Returns (full dates, (year, month) pairs for month-only dates)."""
    full, spans = [], []
    for pattern in _FULL:
        for match in pattern.finditer(quote):
            parsed = _parse(match.group(0))
            if parsed:
                full.append(parsed)
                spans.append(match.span())
    months = [(d.year, d.month) for d in _month_only(quote, spans)]
    return full, months


def date_matches(fact_value: str, quote: str) -> tuple[bool, str]:
    target = date.fromisoformat(str(fact_value)[:10])
    full, months = parse_dates(quote)
    if target in full:
        return True, target.isoformat()
    if (target.year, target.month) in months:
        return True, f"{target.year}-{target.month:02d} (month only)"
    shown = [d.isoformat() for d in full] + [f"{y}-{m:02d}" for y, m in months]
    return False, ", ".join(shown)


def _parse(text: str) -> date | None:
    text = re.sub(r"[\"”'’`]", " ", text)
    try:
        yearfirst = bool(re.match(r"\d{4}-", text))
        return parser.parse(text, dayfirst=not yearfirst, yearfirst=yearfirst).date()
    except (ValueError, OverflowError):
        return None


def _month_only(quote: str, taken: list[tuple[int, int]]) -> list[date]:
    found = []
    for match in _MONTH_ONLY.finditer(quote):
        if any(a <= match.start() < b for a, b in taken):
            continue
        parsed = _parse(f"1 {match.group(0)}")
        if parsed:
            found.append(parsed)
    return found

"""Python checks that an item's dates are in an order that makes sense: work starts
before it ends, is awarded before it ends, and its certificate is dated after the work
started, on or before the bid due date, and (for a completed project) not before the
work ended. A date out of order is flagged for the committee, never corrected: it may
be a misread date, an unusual contract, or an altered document.

The certificate date counts only when its quote is found on its page, since it is
asked for only to make this check.
"""
from datetime import date

from app.config import Settings
from app.evaluate.condition_check import parse_value
from app.evaluate.evidence_check import check_fact
from app.schemas.llm import ItemResult
from app.schemas.records import EvidenceCheck, Item, Page

DATE_ORDER = "date order"


def date_order(result: ItemResult, item: Item, pages: dict[int, Page], settings: Settings,
               as_of: date) -> list[EvidenceCheck]:
    """One check of the item's dates, or none when fewer than two can be compared."""
    dates = _dates(result, item, pages, settings)
    done = result.facts.get("is_completed")
    completed = bool(done) and str(done.value).lower() == "true"
    problems = _problems(dates, as_of, completed)
    if len([d for d in dates.values() if d]) < 2 and not problems:
        return []
    base = {"label": result.label, "fact": DATE_ORDER, "quote_found": True}
    if not problems:
        return [EvidenceCheck(**base, value_matches=True, note="The dates are in order.")]
    return [EvidenceCheck(**base, value_matches=False,
                          note="Dates out of order: " + "; ".join(problems) + ".")]


def _dates(result: ItemResult, item: Item, pages: dict[int, Page],
           settings: Settings) -> dict[str, date | None]:
    facts = result.facts
    dates = {name: _date(facts.get(name)) for name in ("awarded_on", "start_on", "end_on")}
    issued = facts.get("certificate_on")
    found = issued and check_fact(item, "certificate_on", issued, pages, settings).passed()
    dates["certificate_on"] = _date(issued) if found else None
    return dates


def _problems(d: dict[str, date | None], as_of: date, completed: bool) -> list[str]:
    rules = [
        ("start_on", "end_on", "the work starts ({0}) after it ends ({1})"),
        ("awarded_on", "end_on", "it was awarded ({0}) after the work ended ({1})"),
        ("start_on", "certificate_on", "the certificate ({1}) is dated before the work "
                                       "started ({0})")]
    found = [text.format(_show(d[a]), _show(d[b])) for a, b, text in rules
             if d[a] and d[b] and d[a] > d[b]]
    cert = d["certificate_on"]
    if cert and cert > as_of:
        found.append(f"the certificate ({_show(cert)}) is dated after the bid due date "
                     f"({_show(as_of)})")
    if completed and cert and d["end_on"] and cert < d["end_on"]:
        found.append(f"the completion certificate ({_show(cert)}) is dated before the work "
                     f"ended ({_show(d['end_on'])})")
    return found


def _date(fact) -> date | None:
    value = parse_value(fact.value) if fact else None
    return value if isinstance(value, date) else None


def _show(day: date) -> str:
    return f"{day.day} {day:%b %Y}"

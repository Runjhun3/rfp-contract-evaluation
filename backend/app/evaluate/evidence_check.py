"""Python verifies the evidence behind every item the LLM relied on.

1. An eligible PROJECT cites a work-order page and a completion/CA page inside the item.
2. Every fact in relies_on has a quote that is on its cited page (inside the item).
3. Amount and date quotes actually state the value used.
Failures are recorded, never corrected.
"""
from app.config import Settings
from app.evaluate.parse_amount import amount_matches
from app.evaluate.parse_date import date_matches
from app.evaluate.quote_match import quote_score
from app.schemas.llm import Fact, ItemResult
from app.schemas.records import EvidenceCheck, Item, Page

AMOUNT_FACTS = {"value_inr"}
DATE_FACTS = {"awarded_on", "start_on", "end_on"}
ALIASES = {"duration": ["start_on", "end_on"], "duration_months": ["start_on", "end_on"]}


def check_item(result: ItemResult, item: Item, pages: dict[int, Page],
               settings: Settings) -> list[EvidenceCheck]:
    checks = []
    if result.eligible and item.kind == "PROJECT":
        checks.append(_presence("work_order", result.evidence.work_order, item))
        checks.append(_presence("completion_or_ca", result.evidence.completion_or_ca, item))
    facts = result.all_facts()
    for name in _expand(result.relies_on):
        checks.append(_check_fact(item, name, facts.get(name), pages, settings))
    return checks


def _expand(names: list[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        for real in ALIASES.get(name, [name]):
            if real not in out:
                out.append(real)
    return out


def _presence(name: str, cited: list[int], item: Item) -> EvidenceCheck:
    inside = [p for p in cited if item.from_page <= p <= item.to_page]
    note = "" if inside else f"no {name} page cited inside p.{item.from_page}-{item.to_page}"
    return EvidenceCheck(label=item.label, fact=f"{name}_present", quote_found=bool(inside),
                         match_score=100 if inside else 0,
                         pdf_page_no=inside[0] if inside else None, note=note)


def _check_fact(item: Item, name: str, fact: Fact | None, pages: dict[int, Page],
                settings: Settings) -> EvidenceCheck:
    base = {"label": item.label, "fact": name}
    if fact is None or not fact.quote or fact.page is None:
        return EvidenceCheck(**base, quote_found=False, note="no quote given")
    page = pages.get(fact.page)
    if page is None or not item.from_page <= fact.page <= item.to_page:
        return EvidenceCheck(**base, pdf_page_no=fact.page, quote=fact.quote,
                             quote_found=False, note="cited page is outside the item")
    score = quote_score(fact.quote, page.full_text())
    found = score >= settings.quote_match_threshold
    matches, parsed = _value_check(name, fact, settings)
    note = "" if found else "quote not found on cited page"
    return EvidenceCheck(**base, pdf_page_no=fact.page, quote=fact.quote, quote_found=found,
                         match_score=score, parsed_value=parsed, value_matches=matches, note=note)


def _value_check(name: str, fact: Fact, settings: Settings) -> tuple[bool | None, str | None]:
    if fact.value in (None, ""):
        return None, None
    try:
        if name in AMOUNT_FACTS:
            return amount_matches(fact.value, fact.quote or "", settings.amount_tolerance)
        if name in DATE_FACTS:
            return date_matches(fact.value, fact.quote or "")
    except ValueError as err:
        return False, f"unreadable value: {err}"
    return None, None

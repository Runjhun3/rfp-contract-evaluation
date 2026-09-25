"""Group copies of the same project (submitted under different criteria) and check
they agree on client, value and dates. Deterministic, standard library only.
"""
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from app.evaluate.quote_match import normalise
from app.schemas.llm import ItemResult
from app.schemas.records import CopyGroup, Item

SAME_PROJECT = 0.80
COMPARED = ("client", "value_inr", "awarded_on", "start_on", "end_on")


def check_copies(items: list[Item], results: dict[str, ItemResult]) -> list[CopyGroup]:
    projects = [i for i in items if i.kind == "PROJECT" and i.label in results]
    groups: list[list[Item]] = []
    for item in projects:
        home = next((g for g in groups if _same_project(g[0], item, results)), None)
        home.append(item) if home else groups.append([item])
    return [CopyGroup(labels=[i.label for i in g], mismatches=_mismatches(g, results))
            for g in groups if len(g) > 1]


def _key(item: Item, result: ItemResult) -> str:
    title = _value(result, "title") or item.title
    return normalise(f"{_value(result, 'client') or ''} {title}")


def _same_project(a: Item, b: Item, results: dict[str, ItemResult]) -> bool:
    if a.criterion_code == b.criterion_code:
        return False
    ratio = SequenceMatcher(None, _key(a, results[a.label]), _key(b, results[b.label])).ratio()
    return ratio >= SAME_PROJECT


def _mismatches(group: list[Item], results: dict[str, ItemResult]) -> list[str]:
    problems = []
    for field in COMPARED:
        values = {_canon(field, _value(results[i.label], field)) for i in group}
        values.discard(None)
        if len(values) > 1:
            problems.append(f"{field}: {sorted(values)}")
    return problems


def _value(result: ItemResult, field: str) -> str | None:
    fact = result.facts.get(field)
    return fact.value if fact and fact.value not in (None, "") else None


def _canon(field: str, value: str | None) -> str | None:
    if value is None:
        return None
    if field == "value_inr":
        try:
            return str(Decimal(value.replace(",", "")).quantize(Decimal("1E5")))
        except InvalidOperation:
            return value
    return normalise(value)[:10] if field != "client" else normalise(value)

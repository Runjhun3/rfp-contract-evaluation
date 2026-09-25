"""Decide needs_review and why, for one criterion. Codes: docs/pipeline.md."""
from app.config import Settings
from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import ArithmeticCheck, CopyGroup, EvidenceCheck, Item, Page


def review_reasons(result: CriterionResult, arith: ArithmeticCheck,
                   items: dict[str, Item], item_results: dict[str, ItemResult],
                   checks: list[EvidenceCheck], copies: list[CopyGroup],
                   pages: dict[int, Page], settings: Settings) -> list[str]:
    counted = {i.label for i in result.items if i.counted}
    judged = {i.label for i in result.items}
    reasons = set()
    if not arith.ok:
        reasons.add("ARITHMETIC")
    if any(c.label in counted and not c.passed() for c in checks):
        reasons.add("EVIDENCE_UNVERIFIED")
    mismatched = {label for g in copies if g.mismatches for label in g.labels}
    if counted & mismatched:
        reasons.add("COPY_MISMATCH")
    threshold = float(settings.review_confidence)
    if any(items[label].map_confidence < threshold for label in judged if label in items):
        reasons.add("MAPPING_UNSURE")
    for label in judged & set(item_results):
        reasons |= _item_reasons(item_results[label], label in counted, pages, threshold)
    return sorted(reasons)


def _item_reasons(result: ItemResult, counted: bool, pages: dict[int, Page],
                  threshold: float) -> set[str]:
    reasons = set()
    if result.confidence < threshold:
        reasons.add("LOW_CONFIDENCE")
    if result.suspicious_text:
        reasons.add("SUSPICIOUS_TEXT")
    facts = result.all_facts()
    if result.eligible and any(facts.get(n) is None for n in result.relies_on
                               if n not in ("duration", "duration_months")):
        reasons.add("MISSING_FACT")
    cited = result.evidence.work_order + result.evidence.completion_or_ca
    if counted and any(pages.get(n) and pages[n].ocr_text for n in cited):
        reasons.add("OCR_EVIDENCE")
    return reasons

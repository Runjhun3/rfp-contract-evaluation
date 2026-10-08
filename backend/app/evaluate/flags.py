"""Decide needs_review and why, for one criterion. Codes: docs/pipeline.md."""
from app.config import Settings
from app.evaluate.condition_check import PREFIX
from app.evaluate.document_checks import REASONS
from app.evaluate.evidence_check import CV_CHECKED
from app.evaluate.proof_check import PROOF
from app.evaluate.rejection_check import REJECTION
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
    if any(c.label in counted and not c.passed() for c in checks
           if not c.fact.startswith(PREFIX) and c.fact not in (REJECTION, PROOF, *REASONS)):
        reasons.add("EVIDENCE_UNVERIFIED")
    reasons |= {REASONS[c.fact] for c in checks
                if c.label in judged and c.fact in REASONS and c.value_matches is False}
    if any(c.label in judged and c.value_matches is False for c in checks
           if c.fact.startswith(PREFIX)):
        reasons.add("CONDITION_MISMATCH")
    if any(c.label in judged and c.fact == REJECTION and c.value_matches is False
           for c in checks):
        reasons.add("UNSUPPORTED_REJECTION")
    if any(c.label in judged and c.fact == PROOF and c.value_matches is False for c in checks):
        reasons.add("NO_PROOF")
    if not judged:
        reasons.add("NO_ITEMS_FOUND")
    if any(i.duplicate_of and i.criterion_code == result.code for i in items.values()):
        reasons.add("DUPLICATE_CV")
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
    if result.recheck:
        reasons.add("RECHECKED")
    facts = result.all_facts()
    if result.eligible and any(facts.get(n) is None for n in result.relies_on
                               if n not in ("duration", "duration_months")
                               and not (result.cv and n in CV_CHECKED)):
        reasons.add("MISSING_FACT")
    cited = result.evidence.work_order + result.evidence.completion_or_ca
    if counted and any(pages.get(n) and pages[n].ocr_text for n in cited):
        reasons.add("OCR_EVIDENCE")
    return reasons

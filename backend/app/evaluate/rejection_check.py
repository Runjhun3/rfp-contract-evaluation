"""Python checks that every rejection rests on a hard fail, and gathers what the
item's single re-check is about.

A rejection is backed only by one of:
  - missing_document: a required document the LLM says is not on the item's pages,
  - failed_test: a test in its conditions that is not met, and that Python either
    recomputes as not met or cannot recompute,
  - rfp_exclusion: an exclusion the RFP states, quoted.
Anything else (a doubt about a category, type or relevance) is a judgement call for
the committee. This module knows no RFP rule; it only checks the answer's structure.
"""
from datetime import date

from app.evaluate.condition_check import PREFIX, condition_checks
from app.evaluate.proof_check import PROOF, proof_check
from app.schemas.llm import ItemResult
from app.schemas.records import EvidenceCheck

REJECTION = "rejection"


def answer_checks(result: ItemResult, as_of: date) -> list[EvidenceCheck]:
    """Every recomputed test, whether the result explains itself (reason + quotes),
    and a record of why the item was rejected, if it was."""
    tests = condition_checks(result, as_of)
    rejected = [] if result.eligible else [rejection_check(result, tests)]
    return tests + [proof_check(result)] + rejected


def findings(checks: list[EvidenceCheck]) -> list[str]:
    """What the re-check must look at: tests Python recomputed differently, a missing
    reason or proof, and a rejection without a hard fail."""
    return [c.note for c in checks if c.value_matches is False
            and (c.fact.startswith(PREFIX) or c.fact in (REJECTION, PROOF))]


def rejection_check(result: ItemResult, tests: list[EvidenceCheck]) -> EvidenceCheck:
    fail = result.hard_fail
    backed = fail is not None and bool(fail.detail) and (
        fail.kind == "missing_document"
        or (fail.kind == "rfp_exclusion" and bool(fail.rfp_quote))
        or (fail.kind == "failed_test" and _test_fails(result, fail.fact, tests)))
    base = {"label": result.label, "fact": REJECTION, "quote_found": True}
    if backed:
        return EvidenceCheck(**base, quote=fail.rfp_quote,
                             note=f"not eligible: {fail.kind.replace('_', ' ')}: {fail.detail}")
    given = f" ({fail.kind}: {fail.detail})" if fail else ""
    return EvidenceCheck(**base, value_matches=False,
                         note=f"not eligible without a hard fail{given}. A hard fail is a "
                              "missing required document, a test in conditions that is not "
                              "met, or an exclusion the RFP states; a doubt about a category, "
                              "type or relevance is a judgement call for the committee")


def _test_fails(result: ItemResult, fact: str | None, tests: list[EvidenceCheck]) -> bool:
    """A listed test on that fact is not met, and Python does not recompute it as met."""
    by_name = {c.fact: c for c in tests}
    for cond in result.conditions:
        if cond.fact != fact or cond.met:
            continue
        check = by_name.get(f"{PREFIX}{cond.fact} {cond.test} {cond.threshold}")
        if check is None or check.value_matches is not False:
            return True
    return False

"""Python checks that every item result explains itself: a reason, and for anything
that earns marks at least one exact quote (page + words) behind it; for a CV, a
reason for each sub-criterion. It checks only that the explanation is there (the
quotes themselves are verified on their pages by evidence_check.py), never the rule.
"""
from app.schemas.llm import ItemResult
from app.schemas.records import EvidenceCheck

PROOF = "reason and proof"


def proof_check(result: ItemResult) -> EvidenceCheck:
    missing = []
    if not result.reason.strip():
        missing.append("no reason was given")
    if (result.eligible or result.marks > 0) and not _quoted(result):
        missing.append("no quoted evidence (page and exact words) supports the marks")
    if result.cv:
        missing += [f"sub-criterion '{s.name}' has no reason" for s in result.cv.sub_scores
                    if not s.reason.strip()]
    base = {"label": result.label, "fact": PROOF, "quote_found": True}
    if not missing:
        return EvidenceCheck(**base, note="reason given with quoted evidence")
    return EvidenceCheck(**base, value_matches=False,
                         note=f"Reason or proof missing: {'; '.join(missing)}. Give the reason "
                              "and the exact quotes (page and words) behind the marks")


def _quoted(result: ItemResult) -> bool:
    facts = [f for f in result.all_facts().values() if f and f.quote and f.page]
    rows = result.cv.employment if result.cv else []
    return bool(facts) or any(j.quote and j.page for j in rows)

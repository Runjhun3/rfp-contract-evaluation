from decimal import Decimal

from app.criteria import group_codes, group_mismatches, missing_max_marks, review_view, scored_total
from app.ingest.extract_criteria import (ExtractedCriterion, GeneralCondition, build_block,
                                         merge)


def row(code, max_marks, kind="PROJECT", scored_by="LLM", stage="TECHNICAL", parent=None):
    return {"code": code, "max_marks": max_marks, "kind": kind, "scored_by": scored_by,
            "stage": stage, "parent_code": parent, "rfp_text": "t", "meaning": "m",
            "max_items": None}


# A hypothetical 100-mark RFP: group A (40) = A.1 + A.2, group B (30) has a nested
# group B.1 (20) = B.1.a + B.1.b, then B.2, and a committee-scored C.
def tender(a_marks="40"):
    d = Decimal
    return [row("E.1", None, kind=None, stage="ELIGIBILITY"),
            row("A", d(a_marks), kind=None), row("A.1", d("25"), parent="A"),
            row("A.2", d("15"), parent="A"),
            row("B", d("30"), kind=None), row("B.1", d("20"), kind=None, parent="B"),
            row("B.1.a", d("12"), kind="CV", parent="B.1"),
            row("B.1.b", d("8"), kind="CV", parent="B.1"), row("B.2", d("10"), parent="B"),
            row("C", d("30"), kind=None, scored_by="COMMITTEE")]


def test_ai_scored_criterion_without_max_marks_is_reported():
    rows = [row("A.1", Decimal("16")), row("T.1", None), row("T.2", None, kind="CV")]
    message = missing_max_marks(rows)
    assert message.startswith("T.1, T.2: no max marks")


def test_rows_the_ai_does_not_score_are_ignored():
    rows = [row("A.1", Decimal("16")), row("T.3", None, kind=None),
            row("C", None, scored_by="COMMITTEE"), row("E.1", None, stage="ELIGIBILITY")]
    assert missing_max_marks(rows) is None


def test_group_headings_are_not_added_to_the_total():
    assert scored_total(tender()) == Decimal("100")


def test_group_headings_are_found_at_any_depth():
    assert group_codes(tender()) == {"A", "B", "B.1"}
    view = review_view(tender())
    assert [r["code"] for r in view["criteria"] if r["is_group"]] == ["A", "B", "B.1"]
    assert view["technical_total"] == Decimal("100") and view["group_warnings"] == []


def test_group_marks_that_differ_from_their_parts_are_reported_not_corrected():
    rows = tender(a_marks="36")
    assert group_mismatches(rows) == ["A: the RFP gives 36 marks, but its sub-criteria add "
                                      "up to 40. Check the marks against the RFP."]
    assert scored_total(rows) == Decimal("100")


def test_group_headings_stay_out_of_the_rule_text():
    block = build_block(tender())
    assert "CRITERION A.1 " in block and "CRITERION B.1.a " in block
    assert "CRITERION A " not in block and "CRITERION B " not in block
    assert "CRITERION B.1 " not in block


def test_rule_text_starts_with_general_conditions_and_skips_rows_the_ai_does_not_score():
    rows = tender() + [row("T.9", None, kind=None)]         # e.g. a declaration, not scored per item
    block = build_block(rows, [GeneralCondition(text="Experience must be from India.", rfp_page=36)])
    assert block.index("GENERAL CONDITIONS") < block.index("CRITERION A.1 ")
    assert '- "Experience must be from India." [RFP p. 36]' in block
    assert "CRITERION T.9" not in block


def extracted(code, stage="ELIGIBILITY", title=None):
    return ExtractedCriterion(code=code, stage=stage, title=title or code, rfp_text="t",
                              meaning="m")


def test_eligibility_rows_from_several_chunks_are_numbered_once_each():
    chunk_1 = [extracted("E.1", title="Bid Security"), extracted("E.2", title="Empanelment"),
               extracted("A.1", "TECHNICAL")]
    chunk_2 = [extracted("E.1", title="Bid Submission Form"),
               extracted("E.2", title="bid  security"),          # same row seen again
               extracted("A.1", "TECHNICAL", title="later copy")]
    rows = merge(chunk_1 + chunk_2)
    assert [(r.code, r.title) for r in rows] == [
        ("E.1", "Bid Security"), ("E.2", "Empanelment"), ("E.3", "Bid Submission Form"),
        ("A.1", "A.1")]

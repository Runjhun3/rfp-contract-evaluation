import json
from datetime import date
from decimal import Decimal

from app.config import Settings
from app.evaluate.condition_check import condition_checks, findings
from app.evaluate.evidence_check import check_item
from app.evaluate.flags import review_reasons
from app.evaluate.item_eval import evaluate_item
from app.llm.client import LlmClient
from app.schemas.llm import (Condition, CriterionItem, CriterionResult, CvFacts, Fact,
                             ItemResult, Job, Recheck)
from app.schemas.records import ArithmeticCheck, Item, Page, RunContext

AS_OF = date(2026, 5, 7)
ITEM = Item(label="A.3 p.1-2", title="t", kind="PROJECT", criterion_code="A.3",
            map_confidence=0.9, from_page=1, to_page=2)
CTX = RunContext(tender_no="T", department="D", bidder="B", bid_due_date=AS_OF)


def result(*conds, eligible=False, marks="0", **facts):
    return ItemResult(label=ITEM.label, code="A.3", eligible=eligible, marks=Decimal(marks),
                      reason="r", confidence=0.9,
                      facts={k: Fact(value=v, page=1, quote=v) for k, v in facts.items()},
                      conditions=[Condition(fact=f, test=t, threshold=th, met=m)
                                  for f, t, th, m in conds])


def test_amount_test_the_llm_got_wrong_is_found():
    r = result(("value_inr", ">", "50000000", False), value_inr="58900000")
    checks = condition_checks(r, AS_OF)
    assert checks[0].value_matches is False
    assert findings(checks) == ["value_inr = 58900000: > 50000000 is true, "
                                "the evaluation said false"]


def test_band_boundaries_date_cut_off_and_duration_are_recomputed():
    r = result(("value_inr", ">", "20000000", True), ("value_inr", ">", "50000000", True),
               ("awarded_on", "<=", "2025-05-07", True), ("duration_months", ">=", "12", True),
               value_inr="50200000", awarded_on="2021-07-22", start_on="2020-01-22",
               end_on="2022-01-21")
    checks = condition_checks(r, AS_OF)
    assert [c.value_matches for c in checks] == [True, True, True, True]
    assert checks[3].parsed_value == "24.0"          # 22 Jan 2020 to 21 Jan 2022, inclusive


def test_cv_years_come_from_the_employment_rows_not_the_llm():
    r = result(("experience_years", ">=", "10", False))
    r.cv = CvFacts(employment=[Job(start="2012-03", end="2013-05"),
                               Job(start="2015-05", end="present")],
                   experience_years=Decimal(5))
    assert condition_checks(r, AS_OF)[0].value_matches is False     # 1.2 + 11.0 years


def test_a_test_that_cannot_be_recomputed_is_recorded_not_guessed():
    r = result(("client_type", "=", "government", True), ("value_inr", "~", "1", True),
               value_inr="100")
    checks = condition_checks(r, AS_OF)
    assert all(c.value_matches is None for c in checks) and findings(checks) == []
    assert "could not recompute" in checks[0].note


def fake_llm(tmp_path, answers):
    calls = []

    def complete(system, user, images):
        calls.append(user)
        return json.dumps(answers[len(calls) - 1])

    return LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path)), complete), calls


def answer(eligible, marks, met):
    return {"label": "x", "code": "x", "eligible": eligible, "marks": marks, "reason": "why",
            "confidence": 0.9, "facts": {"value_inr": {"value": "58900000", "page": 1,
                                                       "quote": "INR 5.89 Cr"}},
            "conditions": [{"fact": "value_inr", "test": ">", "threshold": "50000000",
                            "met": met}]}


PAGES = {1: Page(pdf_page_no=1, text="Contract value INR 5.89 Cr"),
         2: Page(pdf_page_no=2, text="")}


def test_a_wrong_test_sends_the_item_back_once_and_both_answers_are_kept(tmp_path):
    llm, calls = fake_llm(tmp_path, [answer(False, "0", False), answer(True, "2.5", True)])
    final = evaluate_item(ITEM, PAGES, CTX, "system", llm)
    assert len(calls) == 2 and "value_inr = 58900000: > 50000000 is true" in calls[1]
    assert final.eligible and final.marks == Decimal("2.5")
    assert final.recheck.first_marks == 0 and not final.recheck.first_eligible
    note = [c for c in check_item(final, ITEM, PAGES, Settings(_env_file=None), AS_OF)
            if c.fact == "re-checked"][0].note
    assert note.startswith("First answer: not eligible, 0 marks.")
    assert note.endswith("After re-check: eligible, 2.5 marks.")


def test_a_correct_answer_is_not_sent_back(tmp_path):
    llm, calls = fake_llm(tmp_path, [answer(True, "2.5", True)])
    assert evaluate_item(ITEM, PAGES, CTX, "system", llm).recheck is None and len(calls) == 1


def test_flags_for_a_recheck_and_for_a_test_still_wrong_after_it():
    still_wrong = result(("value_inr", ">", "50000000", False), value_inr="58900000")
    rechecked = result(("value_inr", ">", "50000000", True), eligible=True, marks="2.5",
                       value_inr="58900000")
    rechecked.recheck = Recheck(first_eligible=False, first_marks=Decimal(0), first_reason="r",
                                findings=["x"])
    for r, expected in ((still_wrong, "CONDITION_MISMATCH"), (rechecked, "RECHECKED")):
        row = CriterionItem(label=ITEM.label, order=1, eligible=r.eligible, counted=r.eligible,
                            marks=r.marks, reason="r")
        reasons = review_reasons(
            CriterionResult(code="A.3", items=[row], counted_items=1, marks=r.marks, summary=""),
            ArithmeticCheck(code="A.3", llm_marks=r.marks, checked_marks=r.marks, ok=True,
                            issues=[]),
            {ITEM.label: ITEM}, {ITEM.label: r}, condition_checks(r, AS_OF), [], PAGES,
            Settings(_env_file=None))
        assert expected in reasons and "EVIDENCE_UNVERIFIED" not in reasons


def test_a_cv_without_dated_rows_is_not_recomputed_as_zero_years():
    r = result(("experience_years", ">=", "7", True))
    r.cv = CvFacts(employment=[Job(organisation="Org", quote="row")], experience_years=Decimal(7))
    checks = condition_checks(r, AS_OF)
    assert checks[0].value_matches is None and findings(checks) == []

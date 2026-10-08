from datetime import date
from decimal import Decimal

from app.evaluate.condition_check import condition_checks
from app.evaluate.rejection_check import findings, rejection_check
from app.evidence_labels import present
from app.schemas.llm import Condition, Fact, HardFail, ItemResult

AS_OF = date(2026, 5, 7)


def result(*conds, eligible=True, **facts):
    return ItemResult(label="A.1 p.1-2", code="A.1", eligible=eligible, marks=Decimal(1),
                      reason="r", confidence=0.9,
                      facts={k: Fact(value=v, page=1, quote=v) for k, v in facts.items()},
                      conditions=[Condition(fact=f, test=t, threshold=th, met=m)
                                  for f, t, th, m in conds])


def shown(check):
    return present(check.model_dump(), {})


def test_a_yes_no_test_is_recomputed_from_its_fact():
    agrees = condition_checks(result(("is_completed", "=", "true", True),
                                     is_completed="true"), AS_OF)[0]
    assert agrees.value_matches is True
    assert shown(agrees) == {"quote": None, "page": None, "label": "Completed",
                             "state": "passed", "detail": "Yes, as the RFP's test requires"}
    differs = condition_checks(result(("is_completed", "=", "true", True),
                                      is_completed="false"), AS_OF)[0]
    assert differs.value_matches is False and shown(differs)["state"] == "problem"
    assert findings([differs]) == ["is_completed = false: = true is false, "
                                   "the evaluation said true"]
    unknown = condition_checks(result(("is_completed", "=", "true", True)), AS_OF)[0]
    assert unknown.value_matches is None and "could not recompute" in unknown.note


def test_a_test_against_words_is_the_ais_judgement_never_compared_letter_by_letter():
    degree = condition_checks(result(("degree", "=", "Post Graduate in Architecture", True),
                                     degree="M.Arch"), AS_OF)[0]
    assert degree.value_matches is None and degree.parsed_value == "M.Arch"
    view = shown(degree)
    assert view["label"] == "Degree equal to Post Graduate in Architecture"
    assert view["state"] == "passed"
    assert view["detail"] == 'Judged by the AI by meaning: met (the document says "M.Arch").'
    unmet = condition_checks(result(("degree", "=", "Post Graduate in Architecture", False),
                                    degree="B.Com"), AS_OF)[0]
    assert shown(unmet)["state"] == "note"


def test_a_failed_test_against_words_still_backs_a_rejection():
    r = result(("degree", "=", "Post Graduate in Architecture", False), eligible=False,
               degree="B.Com")
    r.hard_fail = HardFail(kind="failed_test", detail="Not a postgraduate degree",
                           fact="degree")
    assert rejection_check(r, condition_checks(r, AS_OF)).value_matches is None

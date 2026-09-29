from datetime import date
from decimal import Decimal

from app.evaluate.bounds import parse_range, passing_range, settle, split_bound
from app.evaluate.condition_check import condition_checks
from app.evaluate.parse_amount import amount_matches
from app.evidence_labels import present, show_value
from app.schemas.llm import Condition, Fact, ItemResult

D = Decimal


def test_bounds_are_read_from_words_and_symbols():
    assert parse_range("more than 3000") == (D(3000), True, None, False)
    assert parse_range(">= 5") == (D(5), False, None, False)
    assert parse_range("up to 10") == (None, False, D(10), False)
    assert parse_range("below 2,000") == (None, False, D(2000), True)
    assert parse_range("3000") is None and parse_range("overall 5") is None
    assert split_bound("> 300000000000") == ("lo", "300000000000")


def test_a_bound_settles_a_test_only_when_the_answer_is_certain():
    more_than_3000 = parse_range("more than 3000")
    assert settle(more_than_3000, passing_range(">", D(750))) is True
    assert settle(more_than_3000, passing_range(">", D(5000))) is None       # unknown
    assert settle(more_than_3000, passing_range("<=", D(3000))) is False
    assert settle(parse_range("at least 12"), passing_range(">=", D(12))) is True
    assert settle(parse_range("less than 12"), passing_range(">=", D(12))) is False


def result(value, *conds):
    return ItemResult(label="A.1 p.1-2", code="A.1", eligible=True, marks=D(5), reason="r",
                      confidence=0.9, facts={"value_inr": Fact(value=value, page=1, quote="q")},
                      conditions=[Condition(fact="value_inr", test=t, threshold=th, met=m)
                                  for t, th, m in conds])


def test_conditions_on_a_stated_bound_are_settled_or_left_open():
    checks = condition_checks(result(">30000000000", (">", "7500000000", True),
                                     (">", "50000000000", True),
                                     ("<=", "7500000000", True)), date(2026, 5, 7))
    assert [c.value_matches for c in checks] == [True, None, False]
    assert "cannot be settled from a bound" in checks[1].note


def test_a_bound_value_is_checked_against_the_quote_by_its_number():
    quote = "average annual turnover of more than INR 3,000 crores"
    assert amount_matches("more than 30000000000", quote, D("0.01"))[0]
    assert not amount_matches(">300000000000", quote, D("0.01"))[0]        # 10x off: flagged


def test_a_bound_reads_naturally_on_the_evidence_screen():
    assert show_value("value_inr", "more than 30000000000") == "more than ₹3000 crore"
    shown = present({"fact": "condition: value_inr > 7500000000", "pdf_page_no": 3,
                     "quote": None, "quote_found": True, "match_score": 100,
                     "parsed_value": "more than 30000000000", "value_matches": True,
                     "note": ""}, {})
    assert shown["state"] == "passed" and shown["detail"] == "Yes (more than ₹3000 crore)"

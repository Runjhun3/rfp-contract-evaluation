from decimal import Decimal

from app.config import Settings
from app.evaluate.arithmetic_check import check_criterion
from app.evaluate.copy_check import check_copies
from app.evaluate.evidence_check import check_item
from app.schemas.llm import CriterionItem, CriterionResult, Evidence, Fact, ItemResult
from app.schemas.records import Criterion, Item, Page

SETTINGS = Settings(_env_file=None)
A2 = Criterion(code="A.2", title="t", meaning="m", kind="PROJECT", max_marks=Decimal(10),
               max_items=2, allowed_item_marks=[Decimal(1), Decimal("1.5"), Decimal(2)])


def _item(label="A.2 p.10-12", code="A.2", title="PMU for National Games"):
    return Item(label=label, title=title, kind="PROJECT", criterion_code=code,
                map_confidence=0.95, from_page=10, to_page=12)


def _result(label="A.2 p.10-12", value="90600000", quote="Contract value INR 9.06 Crore",
            page=11, eligible=True, marks="2", client="Sports Authority of Goa"):
    return ItemResult(label=label, code="A.2", eligible=eligible, marks=Decimal(marks),
                      reason="r", confidence=0.9, relies_on=["value_inr"],
                      evidence=Evidence(work_order=[11], completion_or_ca=[12]),
                      facts={"value_inr": Fact(value=value, page=page, quote=quote),
                             "client": Fact(value=client, page=11, quote=client),
                             "title": Fact(value="PMU for National Games", page=10, quote="x")})


PAGES = {10: Page(pdf_page_no=10, text="Project header"),
         11: Page(pdf_page_no=11, text="Work order. Contract value INR 9.06 Crore."),
         12: Page(pdf_page_no=12, text="", ocr_text="Completion certificate")}


def test_evidence_passes():
    checks = check_item(_result(), _item(), PAGES, SETTINGS)
    assert all(c.passed() for c in checks), checks


def test_evidence_wrong_value_fails():
    checks = check_item(_result(value="68000000"), _item(), PAGES, SETTINGS)
    assert any(c.fact == "value_inr" and c.value_matches is False for c in checks)


def test_evidence_quote_not_on_page_fails():
    checks = check_item(_result(quote="Contract value INR 12 Crore"), _item(), PAGES, SETTINGS)
    assert any(c.fact == "value_inr" and not c.quote_found for c in checks)


def test_evidence_page_outside_item_fails():
    checks = check_item(_result(page=40), _item(), PAGES, SETTINGS)
    assert any("outside" in c.note for c in checks)


def test_copies_agree_and_disagree():
    items = [_item(), _item(label="A.3 p.30-32", code="A.3")]
    same = {"A.2 p.10-12": _result(), "A.3 p.30-32": _result(label="A.3 p.30-32")}
    assert check_copies(items, same)[0].mismatches == []
    diff = {"A.2 p.10-12": _result(), "A.3 p.30-32": _result(label="A.3 p.30-32", value="95000000")}
    assert "value_inr" in check_copies(items, diff)[0].mismatches[0]


def _criterion_result(rows, total):
    return CriterionResult(code="A.2", counted_items=sum(r[2] for r in rows), marks=Decimal(total),
                           summary="s", items=[CriterionItem(label=l, order=n, eligible=True,
                                               counted=c, marks=Decimal(m), reason="r")
                                               for n, (l, m, c) in enumerate(rows, 1)])


def test_arithmetic_ok_and_best_n():
    items = {"a": _result("a", marks="2"), "b": _result("b", marks="1.5"), "c": _result("c", marks="1")}
    good = _criterion_result([("a", "2", True), ("b", "1.5", True), ("c", "1", False)], "3.5")
    assert check_criterion(A2, good, items).ok
    bad = _criterion_result([("a", "2", True), ("b", "1.5", False), ("c", "1", True)], "3")
    assert any("not best N" in i for i in check_criterion(A2, bad, items).issues)


def test_arithmetic_wrong_total_and_cap():
    items = {"a": _result("a", marks="2"), "b": _result("b", marks="2"), "c": _result("c", marks="2")}
    wrong = _criterion_result([("a", "2", True), ("b", "2", True), ("c", "2", True)], "6")
    issues = check_criterion(A2, wrong, items).issues
    assert any("maximum is 2" in i for i in issues)

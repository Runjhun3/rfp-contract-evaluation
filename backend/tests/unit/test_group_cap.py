from decimal import Decimal

from app.evaluate.group_cap import CAP_APPLIED, apply_caps

d = Decimal


def row(code, parent=None, cap=None):
    return {"code": code, "parent_code": parent, "group_cap": cap}


def tree(cap=None):
    return [row("E.1"), row("A", cap=cap), row("A.1", "A"), row("A.2", "A"),
            row("B"), row("B.1", "B"), row("B.1.a", "B.1"), row("B.1.b", "B.1"), row("C")]


MARKS = {"A.1": d("25"), "A.2": d("13"), "B.1.a": d("12"), "B.1.b": d("8")}


def test_without_caps_the_document_total_is_the_plain_sum():
    groups, docs = apply_caps(tree(), MARKS)
    assert docs == d("58")
    assert groups["A"] == {"sum": d("38"), "total": d("38"), "flags": []}
    assert groups["B"]["total"] == d("20") and groups["B.1"]["total"] == d("20")


def test_a_cap_keeps_both_numbers_and_marks_the_group():
    groups, docs = apply_caps(tree(cap=d("36")), MARKS)
    assert groups["A"] == {"sum": d("38"), "total": d("36"), "flags": [CAP_APPLIED]}
    assert docs == d("56")


def test_a_cap_that_is_not_reached_changes_nothing():
    groups, docs = apply_caps(tree(cap=d("40")), MARKS)
    assert groups["A"]["total"] == d("38") and groups["A"]["flags"] == []
    assert docs == d("58")


def test_a_nested_cap_feeds_its_capped_total_upwards():
    rows = tree()
    rows[5]["group_cap"] = d("15")                       # B.1
    groups, docs = apply_caps(rows, MARKS)
    assert groups["B.1"]["total"] == d("15") and groups["B"]["sum"] == d("15")
    assert docs == d("53")


def test_groups_without_any_marked_part_are_left_out():
    groups, docs = apply_caps(tree(), {"A.1": d("5")})
    assert "B" not in groups and docs == d("5")

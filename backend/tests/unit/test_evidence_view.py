from decimal import Decimal

from app.evidence_labels import present, show_value
from app.evidence_view import _flags, _groups

T = Decimal("0.80")


def check(fact, **kw):
    base = {"item_id": "i1", "fact": fact, "pdf_page_no": 5, "quote": None, "quote_found": True,
            "match_score": 100, "parsed_value": None, "value_matches": None, "note": ""}
    return {**base, **kw}


def test_values_are_shown_by_their_suffix():
    assert show_value("value_inr", "58900000") == "₹5.89 crore"
    assert show_value("fee_inr", "250000") == "₹2.5 lakh"
    assert show_value("awarded_on", "2021-07-22") == "22 Jul 2021"
    assert show_value("duration_months", "24.0") == "24 months"
    assert show_value("client", "SAI") == "SAI"


def test_a_recomputed_test_reads_as_plain_words():
    wrong = present(check("condition: value_inr > 50000000", parsed_value="58900000",
                          value_matches=False), {})
    assert wrong == {"label": "Contract value above ₹5 crore", "state": "problem",
                     "detail": "Python: Yes (₹5.89 crore); the AI said no",
                     "quote": None, "page": 5}
    right = present(check("condition: awarded_on <= 2025-05-07", parsed_value="2021-07-22",
                          value_matches=True), {})
    assert right["state"] == "passed" and right["detail"] == "Yes (22 Jul 2021)"
    unknown = present(check("condition: client_type = government"), {})
    assert unknown["state"] == "note"


def test_a_quote_that_does_not_state_the_value_names_the_value_used():
    shown = present(check("value_inr", quote_found=True, value_matches=False,
                          parsed_value="2022, 35949, 60000000.00"),
                    {"value_inr": {"value": "68400000"}})
    assert shown["state"] == "problem"
    assert shown["detail"] == "The quote does not state the value used (₹6.84 crore)"
    assert present(check("work_order_present"), {})["label"] == "Work order"
    assert present(check("employment_row_3"), {})["label"] == "Employment row 3"
    assert present(check("some_new_fact"), {})["label"] == "Some new fact"


def item(item_id, counted, confidence="0.9", eligible=True, **kw):
    base = {"item_id": item_id, "title": item_id, "label": item_id, "from_page": 1,
            "to_page": 2, "eligible": eligible, "counted": counted, "marks": Decimal(2),
            "confidence": Decimal(confidence) if confidence else None,
            "map_confidence": Decimal("0.95"),
            "suspicious_text": [], "copy_mismatches": [], "decision": None,
            "decided_marks": None, "decision_reason": None,
            "final_marks": Decimal(2) if counted else Decimal(0), "final_counted": bool(counted)}
    return {**base, **kw}


def test_items_are_grouped_and_flag_only_what_they_caused():
    items = [item("a", True), item("b", False, confidence="0.6"),
             item("c", None, eligible=None, confidence=None)]
    flags = {"a": _flags(items[0], [check("value_inr", item_id="a", quote_found=False)], T),
             "b": _flags(items[1], [check("re-checked", item_id="b")], T),
             "c": _flags(items[2], [], T)}
    assert flags == {"a": {"EVIDENCE_UNVERIFIED"}, "b": {"LOW_CONFIDENCE", "RECHECKED"},
                     "c": set()}
    groups = {g["key"]: [(i["item_id"], i["attention"]) for i in g["items"]]
              for g in _groups(items, flags)}
    assert groups == {"counted": [("a", True)], "not_counted": [("b", True)],
                      "not_scored": [("c", False)]}


def test_an_item_overridden_into_the_count_is_grouped_as_counted():
    moved = item("d", False, decision="OVERRIDE", decided_marks=Decimal(2),
                 final_marks=Decimal(2), final_counted=True)
    groups = {g["key"]: [(i["item_id"], i["marks"], i["decision"]) for i in g["items"]]
              for g in _groups([item("a", True), moved], {"a": set(), "d": set()})}
    assert groups == {"counted": [("a", Decimal(2), None), ("d", Decimal(2), "OVERRIDE")]}


def test_a_decided_item_loses_its_amber_dot():
    flagged = {"LOW_CONFIDENCE"}
    rows = [item("a", True), item("b", True, decision="ACCEPT", decided_marks=Decimal(2))]
    groups = _groups(rows, {"a": flagged, "b": flagged})
    assert [(i["item_id"], i["attention"]) for i in groups[0]["items"]] == [
        ("a", True), ("b", False)]

from decimal import Decimal

import pytest

from app import review

D = Decimal
SCORE = {"run_id": "r", "submission_id": "s", "criterion_id": "c", "max_marks": D(16),
         "checked_marks": D(12)}
ITEMS = [{"item_id": "i1", "counted": True, "marks": D(2)},
         {"item_id": "i2", "counted": False, "marks": D(2)}]


@pytest.fixture
def recorded(monkeypatch):
    rows = []
    monkeypatch.setattr(review.q_results, "score_detail", lambda cur, sid: SCORE)
    monkeypatch.setattr(review.q_results, "items", lambda cur, *a: list(ITEMS))
    monkeypatch.setattr(review.q_results, "record_decision",
                        lambda cur, sid, item, action, marks, reason, user:
                        rows.append((item, action, marks, reason)))
    return rows


def test_accepting_keeps_the_ai_marks_and_needs_no_reason(recorded):
    assert review.decide(None, "x", {"item_id": "i1", "action": "ACCEPT"}, "u") is None
    assert review.decide(None, "x", {"item_id": "i2", "action": "ACCEPT"}, "u") is None
    assert recorded == [("i1", "ACCEPT", D(2), ""), ("i2", "ACCEPT", D(0), "")]


def test_overriding_needs_marks_in_range_and_a_reason(recorded):
    body = {"item_id": "i2", "action": "OVERRIDE", "marks": "2",
            "reason": "Completion certificate accepted by the committee"}
    assert review.decide(None, "x", body, "u") is None
    assert review.decide(None, "x", {**body, "reason": "ok"}, "u").startswith("Give a reason")
    assert review.decide(None, "x", {**body, "marks": "17"}, "u").startswith("Overriding marks")
    assert review.decide(None, "x", {**body, "marks": "two"}, "u").startswith("Enter the")
    assert recorded == [("i2", "OVERRIDE", D(2), body["reason"])]


def test_decisions_are_per_item_when_the_criterion_has_items(recorded):
    assert review.decide(None, "x", {"action": "ACCEPT"}, "u").startswith("Decide each")
    assert review.decide(None, "x", {"item_id": "nope", "action": "ACCEPT"}, "u") \
        .startswith("That item")
    assert recorded == []


@pytest.fixture
def marks_saved(monkeypatch):
    saved, current = [], {}
    tree = [{"criterion_id": "c", "code": "C", "stage": "TECHNICAL", "scored_by": "COMMITTEE",
             "kind": None, "max_marks": D(35), "parent_code": None},
            {"criterion_id": "a", "code": "A.1", "stage": "TECHNICAL", "scored_by": "LLM",
             "kind": "PROJECT", "max_marks": D(10), "parent_code": None}]
    monkeypatch.setattr(review.q_projects, "criteria", lambda cur, t: tree)
    monkeypatch.setattr(review.q_results, "latest_attempts",
                        lambda cur, t: [{"submission_id": "s1"}, {"submission_id": "s2"}])
    monkeypatch.setattr(review.q_results, "manual_marks", lambda cur, ids: {"c": dict(current)})

    def save(cur, s, c, m, reason, u):
        saved.append((s, c, m, reason))
        current[s] = m
    monkeypatch.setattr(review.q_results, "save_manual_mark", save)
    return saved


def test_committee_marks_are_saved_only_for_committee_scored_criteria(marks_saved):
    assert review.save_committee_marks(None, "t", {"c": {"s1": "32", "s2": " "}}, "", "u") is None
    assert marks_saved == [("s1", "c", D(32), "")]         # blank entries are skipped
    too_high = review.save_committee_marks(None, "t", {"c": {"s1": "36"}}, "", "u")
    assert too_high == "C marks must be numbers from 0 to 35."
    not_committee = review.save_committee_marks(None, "t", {"a": {"s1": "5"}}, "", "u")
    assert not_committee.startswith("Those marks")
    assert len(marks_saved) == 1


def test_changing_a_saved_committee_mark_needs_a_reason_and_is_kept(marks_saved):
    assert review.save_committee_marks(None, "t", {"c": {"s1": "32"}}, "", "u") is None
    assert review.save_committee_marks(None, "t", {"c": {"s1": "32.00"}}, "", "u") is None
    assert len(marks_saved) == 1                          # unchanged: not saved again
    assert review.save_committee_marks(None, "t", {"c": {"s1": "30"}}, "typo", "u") == (
        "Give a reason of at least 10 characters for changing saved marks.")
    why = "Second panel member's sheet added"
    assert review.save_committee_marks(None, "t", {"c": {"s1": "30"}}, why, "u") is None
    assert marks_saved[-1] == ("s1", "c", D(30), why)


def test_an_item_override_is_up_to_the_most_one_item_can_earn(recorded):
    listed = {**SCORE, "allowed_item_marks": [D(1), D("1.5"), D(2)]}
    body = {"item_id": "i2", "action": "OVERRIDE", "marks": "6",
            "reason": "Committee accepts the completion certificate"}
    assert review.override_problem(D(6), listed, True) ==         "Overriding marks for one item can be at most 2."
    assert review.override_problem(D("1.75"), listed, True) is None   # any mark up to 2
    assert review.override_problem(D(0), listed, True) is None
    assert review.override_problem(D(-1), listed, True).startswith("Enter the")
    assert review.override_problem(D(12), listed, False) is None      # whole criterion: 0..16
    assert review.override_problem(D(6), SCORE, True) is None          # no list: 0..16
    assert review.override_problem(D(17), SCORE, True).startswith("Overriding marks must be")
    review.q_results.score_detail = lambda cur, sid: listed
    assert review.decide(None, "x", body, "u").startswith("Overriding marks for one item")
    assert recorded == []

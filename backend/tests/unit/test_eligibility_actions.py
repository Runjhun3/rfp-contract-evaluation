import pytest

from app import eligibility_actions

REQS = [{"criterion_id": "e1", "code": "E.1", "number": "1", "stage": "ELIGIBILITY"}]


def check(criterion_id, result="MET", check_id=None):
    return {"check_id": check_id or f"c-{criterion_id}", "criterion_id": criterion_id,
            "file_id": "f2", "result": result, "decision": None}


@pytest.fixture
def recorded(monkeypatch):
    saved = []
    current = [check("e1", "UNSURE", check_id="k1"), check("e2", "MET", check_id="k2")]
    monkeypatch.setattr(eligibility_actions.q_eligibility, "get_check", lambda cur, cid: next(
        ({**c, "tender_id": "t", "submission_id": "s1"} for c in current
         if c["check_id"] == cid), None))
    monkeypatch.setattr(eligibility_actions.q_eligibility, "current",
                        lambda cur, t, s=None: current)
    monkeypatch.setattr(eligibility_actions.q_eligibility, "record_decision",
                        lambda cur, cid, d, r, u: saved.append((cid, d, r)))
    return saved


def test_confirming_a_clear_ai_result_needs_no_reason(recorded):
    assert eligibility_actions.decide(None, "k2", {"decision": "MET"}, "u") is None
    assert recorded == [("k2", "MET", "")]


def test_a_reason_is_needed_when_the_ai_was_unsure_or_the_committee_disagrees(recorded):
    assert eligibility_actions.decide(None, "k1", {"decision": "MET"}, "u") == (
        "Give a reason of at least 10 characters: the AI was unsure.")
    assert eligibility_actions.decide(None, "k2", {"decision": "NOT_MET", "reason": "no"}, "u") == (
        "Give a reason of at least 10 characters: you disagree with the AI.")
    assert eligibility_actions.decide(None, "k1", {"decision": "MET",
                                           "reason": "Verified on the original"}, "u") is None
    assert eligibility_actions.decide(None, "k2", {"decision": "maybe"}, "u") == (
        "Choose whether the bid meets the requirement.")
    assert eligibility_actions.decide(None, "zz", {"decision": "MET"}, "u") == "Check not found"
    assert recorded == [("k1", "MET", "Verified on the original")]


def test_a_replaced_check_cannot_be_decided(recorded, monkeypatch):
    newer = [check("e1", "MET", check_id="k9")]
    monkeypatch.setattr(eligibility_actions.q_eligibility, "current", lambda cur, t, s=None: newer)
    assert eligibility_actions.decide(None, "k1", {"decision": "MET", "reason": "x" * 12}, "u") == (
        "This check was replaced by a newer one. Reload the page.")


def test_checks_are_queued_only_after_approval_and_only_with_requirements(monkeypatch):
    queued = []
    prompt = {"status": "DRAFT"}
    monkeypatch.setattr(eligibility_actions.q_projects, "latest_prompt", lambda cur, t: prompt)
    monkeypatch.setattr(eligibility_actions, "requirements", lambda cur, t: REQS)
    monkeypatch.setattr(eligibility_actions.q_bids, "ready_submissions",
                        lambda cur, t: [{"submission_id": "s1"}, {"submission_id": "s2"}])
    monkeypatch.setattr(eligibility_actions.q_eligibility, "enqueue_check",
                        lambda cur, t, s, origin: queued.append((s, origin[1])))
    upload = ("u", "Bid uploaded")
    assert eligibility_actions.queue_checks(None, "t", upload) == 0
    assert eligibility_actions.start(None, "t", "u") == "Approve the criteria first."
    prompt["status"] = "APPROVED"
    assert eligibility_actions.queue_checks(None, "t", upload, ["s2"]) == 1
    assert eligibility_actions.start(None, "t", "u") is None
    assert queued == [("s2", "Bid uploaded"), ("s1", "Check eligibility again"),
                      ("s2", "Check eligibility again")]

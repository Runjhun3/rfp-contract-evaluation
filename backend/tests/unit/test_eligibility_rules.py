import pytest

from app import eligibility

REQS = [{"criterion_id": "e1", "code": "E.1", "stage": "ELIGIBILITY"},
        {"criterion_id": "e2", "code": "E.2", "stage": "ELIGIBILITY"}]
DOC = {"criterion_id": "d1", "code": "D.1", "stage": "DOCUMENT"}
BID = {"submission_id": "s1", "short_name": "Firm A", "legal_name": "Firm A Pvt Ltd",
       "included": True, "file_id": "f2"}


def check(criterion_id, result="MET", decision=None, file_id="f2", check_id=None):
    return {"check_id": check_id or f"c-{criterion_id}", "criterion_id": criterion_id,
            "file_id": file_id, "result": result, "decision": decision}


def status(checks, job=None, reqs=REQS):
    row = eligibility.firm(BID, reqs, checks, job)
    return row["status"], row["label"]


def test_a_firm_qualifies_only_when_the_committee_decides_every_check_as_met():
    assert status([check("e1", decision="MET"), check("e2", decision="MET")]) == (
        "qualified", "Qualified")
    # The AI said met for both, but nothing is decided: the firm waits.
    assert status([check("e1"), check("e2")]) == ("open", "2 to decide")
    assert status([check("e1", decision="MET"), check("e2", "NOT_MET")]) == (
        "open", "1 to decide")


def test_a_check_decided_as_not_met_disqualifies_once_nothing_is_open():
    decided = [check("e1", decision="MET"), check("e2", "MET", decision="NOT_MET")]
    assert status(decided) == ("not_qualified", "Not qualified: criterion E.2 not met")


def test_the_rfps_own_numbers_are_shown_where_it_prints_them():
    reqs = [dict(REQS[0], rfp_no="1"), dict(REQS[1], rfp_no="2"), dict(DOC, rfp_no="B")]
    decided = [check("e1", decision="MET"), check("e2", decision="NOT_MET"),
               check("d1", decision="NOT_MET")]
    row = eligibility.firm(BID, reqs, decided, None)
    assert [c["number"] for c in row["cells"]] == ["1", "2", "B"]
    assert (row["label"], row["missing"]) == ("Not qualified: criterion 2 not met", ["B"])
    assert eligibility.number({"code": "E.3", "rfp_no": None}) == "E.3"   # none printed


RUNNING = {"status": "RUNNING", "error": None}


def test_while_checked_again_the_last_results_stay_on_display():
    done = [check("e1", decision="MET"), check("e2", decision="MET")]
    row = eligibility.firm(BID, REQS, done, RUNNING)
    assert (row["status"], row["checking"]) == ("qualified", True)
    assert [c["decision"] for c in row["cells"]] == ["MET", "MET"]
    # A replaced bid: the old file's results stay shown until its new check is over.
    old = [dict(c, file_id="f1") for c in done]
    assert eligibility.firm(BID, REQS, old, RUNNING)["status"] == "qualified"


def test_a_firm_being_checked_again_is_not_offered_for_evaluation():
    done = [check("e1", decision="MET"), check("e2", decision="MET")]
    assert eligibility._can_evaluate(eligibility.firm(BID, REQS, done, None))
    assert not eligibility._can_evaluate(eligibility.firm(BID, REQS, done, RUNNING))


def test_an_unticked_firm_keeps_its_results_but_is_left_out_of_runs():
    done = [check("e1", decision="MET"), check("e2", decision="MET")]
    row = eligibility.firm(dict(BID, included=False), REQS, done, None)
    assert (row["status"], row["included"]) == ("qualified", False)
    assert not eligibility._can_evaluate(row)


def test_once_the_new_check_is_over_old_file_results_no_longer_count():
    old = [check("e1", decision="MET", file_id="f1"), check("e2", decision="MET", file_id="f1")]
    assert status(old) == ("not_checked", "Not checked yet")
    assert status(old, {"status": "FAILED", "error": "boom"}) == ("failed", "Check failed")
    row = eligibility.firm(BID, REQS, old, None)
    assert [c["decision"] for c in row["cells"]] == ["MET", "MET"]     # still shown
    assert status([], RUNNING) == ("checking", "Checking eligibility")  # nothing to show yet


def test_a_document_not_submitted_is_flagged_but_never_disqualifies():
    met = [check("e1", decision="MET"), check("e2", decision="MET")]
    row = eligibility.firm(BID, REQS + [DOC], met + [check("d1", "NOT_MET", "NOT_MET")], None)
    assert (row["status"], row["missing"], row["open"]) == ("qualified", ["D.1"], 0)


def test_an_undecided_document_stays_open_without_holding_the_firm_back():
    met = [check("e1", decision="MET"), check("e2", decision="MET")]
    row = eligibility.firm(BID, REQS + [DOC], met + [check("d1")], None)
    assert (row["status"], row["missing"], row["open"]) == ("qualified", [], 1)
    only_documents = eligibility.firm(BID, [DOC], [check("d1", decision="MET")], None)
    assert only_documents["label"] == "No eligibility criteria"


def test_requirements_come_as_criteria_then_documents_in_number_order(monkeypatch):
    rows = [{"code": c, "stage": "ELIGIBILITY"} for c in ("E.10", "E.2", "E.1")]
    rows += [{"code": c, "stage": "DOCUMENT"} for c in ("D.2", "D.1")]
    monkeypatch.setattr(eligibility.q_projects, "criteria",
                        lambda cur, t: rows + [{"code": "A.1", "stage": "TECHNICAL"}])
    assert [r["code"] for r in eligibility.requirements(None, "t")] == [
        "E.1", "E.2", "E.10", "D.1", "D.2"]


def test_without_eligibility_criteria_every_firm_with_a_bid_qualifies():
    assert status([], reqs=[]) == ("qualified", "No eligibility criteria")


@pytest.fixture
def recorded(monkeypatch):
    saved = []
    current = [check("e1", "UNSURE", check_id="k1"), check("e2", "MET", check_id="k2")]
    monkeypatch.setattr(eligibility.q_eligibility, "get_check", lambda cur, cid: next(
        ({**c, "tender_id": "t", "submission_id": "s1"} for c in current
         if c["check_id"] == cid), None))
    monkeypatch.setattr(eligibility.q_eligibility, "current",
                        lambda cur, t, s=None: current)
    monkeypatch.setattr(eligibility.q_eligibility, "record_decision",
                        lambda cur, cid, d, r, u: saved.append((cid, d, r)))
    return saved


def test_confirming_a_clear_ai_result_needs_no_reason(recorded):
    assert eligibility.decide(None, "k2", {"decision": "MET"}, "u") is None
    assert recorded == [("k2", "MET", "")]


def test_a_reason_is_needed_when_the_ai_was_unsure_or_the_committee_disagrees(recorded):
    assert eligibility.decide(None, "k1", {"decision": "MET"}, "u") == (
        "Give a reason of at least 10 characters: the AI was unsure.")
    assert eligibility.decide(None, "k2", {"decision": "NOT_MET", "reason": "no"}, "u") == (
        "Give a reason of at least 10 characters: you disagree with the AI.")
    assert eligibility.decide(None, "k1", {"decision": "MET",
                                           "reason": "Verified on the original"}, "u") is None
    assert eligibility.decide(None, "k2", {"decision": "maybe"}, "u") == (
        "Choose whether the bid meets the requirement.")
    assert eligibility.decide(None, "zz", {"decision": "MET"}, "u") == "Check not found"
    assert recorded == [("k1", "MET", "Verified on the original")]


def test_a_replaced_check_cannot_be_decided(recorded, monkeypatch):
    newer = [check("e1", "MET", check_id="k9")]
    monkeypatch.setattr(eligibility.q_eligibility, "current", lambda cur, t, s=None: newer)
    assert eligibility.decide(None, "k1", {"decision": "MET", "reason": "x" * 12}, "u") == (
        "This check was replaced by a newer one. Reload the page.")


def test_checks_are_queued_only_after_approval_and_only_with_requirements(monkeypatch):
    queued = []
    prompt = {"status": "DRAFT"}
    monkeypatch.setattr(eligibility.q_projects, "latest_prompt", lambda cur, t: prompt)
    monkeypatch.setattr(eligibility, "requirements", lambda cur, t: REQS)
    monkeypatch.setattr(eligibility.q_bids, "ready_submissions",
                        lambda cur, t: [{"submission_id": "s1"}, {"submission_id": "s2"}])
    monkeypatch.setattr(eligibility.q_eligibility, "enqueue_check",
                        lambda cur, t, s: queued.append(s))
    assert eligibility.queue_checks(None, "t") == 0
    assert eligibility.start(None, "t") == "Approve the criteria first."
    prompt["status"] = "APPROVED"
    assert eligibility.queue_checks(None, "t", ["s2"]) == 1 and queued == ["s2"]
    assert eligibility.start(None, "t") is None and queued == ["s2", "s1", "s2"]

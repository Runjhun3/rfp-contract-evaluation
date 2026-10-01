from app import eligibility

REQS = [{"criterion_id": "e1", "code": "E.1", "number": "E.1", "stage": "ELIGIBILITY"},
        {"criterion_id": "e2", "code": "E.2", "number": "E.2", "stage": "ELIGIBILITY"}]
BID = {"submission_id": "s1", "short_name": "Firm A", "legal_name": "Firm A Pvt Ltd",
       "included": True, "file_id": "f2"}


def check(criterion_id, result="MET", decision=None, file_id="f2", check_id=None):
    return {"check_id": check_id or f"c-{criterion_id}", "criterion_id": criterion_id,
            "file_id": file_id, "result": result, "decision": decision}


def status(checks, job=None, reqs=REQS):
    row = eligibility.firm(BID, reqs, checks, job)
    return row["status"], row["label"]


def test_clear_ai_results_qualify_or_disqualify_without_committee_approval():
    assert status([check("e1"), check("e2")]) == ("qualified", "Qualified")
    assert status([check("e1"), check("e2", "NOT_MET")]) == (
        "not_qualified", "Not qualified: criterion E.2 not met")
    assert status([check("e1"), check("e2", "UNSURE")]) == ("open", "1 to decide")


def test_a_check_decided_as_not_met_disqualifies_once_nothing_is_open():
    decided = [check("e1", decision="MET"), check("e2", "MET", decision="NOT_MET")]
    assert status(decided) == ("not_qualified", "Not qualified: criterion E.2 not met")


def test_the_rfps_own_numbers_are_shown_when_it_gives_each_criterion_its_own():
    reqs = eligibility.numbered([dict(REQS[0], rfp_no="(a)"), dict(REQS[1], rfp_no="(b)")])
    decided = [check("e1", decision="MET"), check("e2", decision="NOT_MET")]
    row = eligibility.firm(BID, reqs, decided, None)
    assert [c["number"] for c in row["cells"]] == ["(a)", "(b)"]
    assert row["label"] == "Not qualified: criterion (b) not met"


def test_merged_lists_numbered_from_one_each_get_one_running_number():
    printed = ["1", "2", "3", "1", "2"]                  # a conditions and a documents list
    reqs = eligibility.numbered([{"code": f"E.{i}", "rfp_no": n}
                                 for i, n in enumerate(printed, 1)])
    assert [r["number"] for r in reqs] == ["1", "2", "3", "4", "5"]
    unnumbered = eligibility.numbered([{"code": "E.1", "rfp_no": "7"}, {"code": "E.2"}])
    assert [r["number"] for r in unnumbered] == ["1", "2"]


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


def test_only_considered_eligibility_rows_are_requirements(monkeypatch):
    rows = [{"code": c, "stage": "ELIGIBILITY"} for c in ("E.10", "E.2", "E.1")]
    rows += [{"code": "E.3", "stage": "ELIGIBILITY", "considered": False}]
    monkeypatch.setattr(eligibility.q_projects, "criteria",
                        lambda cur, t: rows + [{"code": "A.1", "stage": "TECHNICAL"}])
    reqs = eligibility.requirements(None, "t")
    assert [(r["code"], r["number"]) for r in reqs] == [("E.1", "1"), ("E.2", "2"),
                                                         ("E.10", "3")]


def test_without_eligibility_criteria_every_firm_with_a_bid_qualifies():
    assert status([], reqs=[]) == ("qualified", "No eligibility criteria")

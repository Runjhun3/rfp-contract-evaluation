from app import audit_view


def row(firm, area, kind, ai, value=None, code="A.1"):
    return {"firm": firm, "stamp": "29 Oct 2026, 11:56:10", "who": "Asha Rao", "area": area,
            "criterion": code, "kind": kind, "value": value, "ai": ai, "reason": None,
            "code": code, "code_label": f"Eligibility {code[2:]}" if code[0] == "E" else code}


def test_only_overrides_are_listed_firm_by_firm(monkeypatch):
    monkeypatch.setattr(audit_view.q_audit, "committee_decisions", lambda cur, t: [
        row("EY", "Marks", "ACCEPT", "2", "2"), row("EY", "Marks", "OVERRIDE", "2", "1"),
        row("GT", "Eligibility", "MET", "MET", code="E.1"),
        row("GT", "Eligibility", "NOT_MET", "MET", code="E.1"),
        row("GT", "Eligibility", "MET", "UNSURE", code="E.2"),
        row("GT", "Committee marks", "MARKS", None, "30", code="A.10")])
    log = audit_view.decision_log(None, "t")
    firms = log["firms"]
    assert [f["firm"] for f in firms] == ["EY", "GT"]
    assert [(r["decision"], r["value"], r["ai"]) for r in firms[0]["rows"]] == [
        ("Marks overridden", "1", "2")]              # accepting the AI is left out
    assert [(r["decision"], r["ai"]) for r in firms[1]["rows"]] == [("Not met", "met")]
    assert firms[0]["summary"] == "1 mark overridden"
    assert firms[1]["summary"] == "1 eligibility result overridden"
    assert log["criteria"] == [{"code": "A.1", "label": "A.1"},
                               {"code": "E.1", "label": "Eligibility 1"}]   # overrides only


def test_criteria_are_in_code_order_with_screened_rows_last(monkeypatch):
    monkeypatch.setattr(audit_view.q_audit, "committee_decisions", lambda cur, t: [
        row("EY", "Eligibility", "NOT_MET", "MET", code="E.2"),
        row("EY", "Marks", "OVERRIDE", "2", "1", code="A.10"),
        row("EY", "Marks", "OVERRIDE", "2", "1", code="A.2")])
    assert [c["code"] for c in audit_view.decision_log(None, "t")["criteria"]] == [
        "A.2", "A.10", "E.2"]


def test_the_activity_log_is_for_administrators_only():
    import asyncio
    from types import SimpleNamespace

    from app.web import routes_audit

    request = SimpleNamespace(session={"role": "COMMITTEE"})
    reply = asyncio.run(routes_audit.activity_page(request))
    assert reply.status_code == 403


def test_a_project_activity_log_offers_its_own_areas_and_pages(monkeypatch):
    asked = []
    rows = [{"stamp": "s", "who": "Asha Rao", "category": "PROJECT", "what": "RFP uploaded",
             "project": "P", "details": "rfp.pdf"}]
    monkeypatch.setattr(audit_view.q_activity, "count", lambda cur, t, f: 101)
    monkeypatch.setattr(audit_view.q_activity, "people", lambda cur: [])
    monkeypatch.setattr(audit_view.q_activity, "actions",
                        lambda cur, t, f, page: asked.append((t, f["categories"], page)) or rows)
    sign_in = audit_view.wanted({"category": "SIGN_IN", "page": "2"}, "t")   # not a project area
    log = audit_view.activity(None, "t", sign_in)
    assert asked[-1] == ("t", audit_view.PROJECT_AREAS, 2) and log["category"] is None
    assert (log["page"], log["pages"], log["total"]) == (2, 3, 101)    # 101 rows: 50 + 50 + 1
    assert log["rows"][0]["area"] == "Projects & RFP"
    assert audit_view.activity(None, "t", audit_view.wanted({"page": "9"}, "t"))["page"] == 3
    audit_view.activity(None, None, audit_view.wanted({"category": "SIGN_IN"}, None))
    assert asked[-1] == (None, ["SIGN_IN"], 1)                   # the central log


def test_filters_that_are_not_an_account_or_a_date_are_ignored():
    asked = audit_view.wanted({"who": "6cf84c6a-eb38-403c-af8d-3dc0f77bc7f9", "since": "2026-10-01",
                               "until": "2026-10-31", "page": "x"}, None)
    assert (asked["who"], asked["since"], asked["until"], asked["page"]) == (
        "6cf84c6a-eb38-403c-af8d-3dc0f77bc7f9", "2026-10-01", "2026-10-31", 1)
    bad = audit_view.wanted({"who": "'; drop table x", "since": "31/10/2026"}, None)
    assert bad["who"] is None and bad["since"] is None


def test_the_csv_never_lets_a_cell_run_as_a_formula():
    from app.export.activity_csv import activity_csv, file_name

    row = {"stamp": "30 Oct 2026, 11:00:00", "who": "Asha Rao", "area": "Participants & bids",
           "what": "Bid uploaded", "project": "Sports", "details": "=HYPERLINK(\"x\")"}
    text = activity_csv([row]).decode("utf-8")
    assert text.startswith("﻿Date & time,Who,Area,What,Project,Details")
    assert "'=HYPERLINK" in text
    assert file_name("Sports Infra / 2", "2026-10-30") == "activity-log-Sports-Infra---2-2026-10-30.csv"
    assert file_name(None, "2026-10-30") == "activity-log-all-projects-2026-10-30.csv"

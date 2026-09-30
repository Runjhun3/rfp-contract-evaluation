"""End-to-end API flow (what the React UI calls) against a real, EMPTY test database,
with a scripted LLM.

Needs: PostgreSQL (DB_* env pointing at a throw-away database; its public schema
is dropped and recreated), and the NSDF PDFs in data/golden/nsdf/.
Run: pytest -m integration
"""
import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.db.connection import transaction
from app.db.migrate import migrate
from app.jobs.worker import run_once
from app.llm.client import LlmClient
from app.web.app import create_app
from tests.integration.scripted_llm import BID, RFP, fake_all

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not (RFP.exists() and BID.exists()), reason="NSDF PDFs not in data/golden/nsdf")
def test_full_flow(tmp_path):
    root = tmp_path
    s = Settings(llm_cache_dir=str(root/'llm'), local_file_dir=str(root/'files'),
                 runs_dir=str(root/'runs'),
                 ocr_engine='tesseract', ocr_min_chars=0, ocr_min_image_ratio=9,
                 app_username='tester', app_password='test-pass-1')
    with transaction(s) as cur:
        cur.execute("drop schema public cascade; create schema public")
    migrate(s)
    llm = LlmClient(s, completer=fake_all)
    c = TestClient(create_app(s), follow_redirects=False)
    def ok(cond, what): assert cond, what
    def data(r): return r.json()["data"]

    ok(c.get("/api/v1/projects").status_code == 401, "API refused before sign-in")
    token = data(c.get("/api/v1/session"))["csrf"]
    r = c.post("/api/v1/login", json={"username": "tester", "password": "wrong"},
               headers={"X-CSRF-Token": token}); ok(r.status_code == 401, "wrong password refused")
    r = c.post("/api/v1/login", json={"username": "tester", "password": "test-pass-1"},
               headers={"X-CSRF-Token": token}); ok(r.status_code == 200, "sign in")
    r = c.get("/api/v1/projects"); ok(r.status_code == 200 and data(r)["projects"] == [], "empty projects list")
    for h, v in [("content-security-policy", "default-src 'self'"), ("x-frame-options", "DENY")]:
        ok(v in r.headers.get(h, ""), f"header {h}")
    ok(c.get("/api/v1/nope").status_code == 404, "unknown API path is a JSON 404")
    r = c.post("/api/v1/projects", json={"name": "x", "due": "2026-05-07"}); ok(r.status_code == 403, "POST without CSRF refused")
    c.headers["X-CSRF-Token"] = data(c.get("/api/v1/session"))["csrf"]
    r = c.post("/api/v1/projects", json={"name": "NSDF PMU 2026", "gem": "GEM/2026/B/7401395",
                                         "department": "Department of Sports, MYAS", "due": "2026-05-07"})
    ok(r.status_code == 201, "project created"); base = f"/api/v1/projects/{data(r)['tender_id']}"
    r = c.post(base + "/rfp", files={"file": ("notes.txt", b"hello", "text/plain")})
    ok(r.status_code == 400 and "not a PDF" in r.json()["message"], "non-PDF upload rejected")
    r = c.post(base + "/rfp", files={"file": ("RFP_Document_NSDF.pdf", open(RFP,'rb').read(), "application/pdf")})
    ok(r.status_code == 201, "RFP uploaded")
    ok(data(c.get(base + "/criteria"))["criteria"] == [], "criteria wait for worker")
    ok(run_once(s, llm), "worker: extract criteria")
    crit = data(c.get(base + "/criteria")); codes = {x["code"]: x for x in crit["criteria"]}
    ok("A.1" in codes and "B.2" in codes and codes["C"]["scored_by"] == "COMMITTEE", "criteria shown")
    r = c.post(base + "/criteria/approve"); ok(r.status_code == 200, "criteria approved")
    r = c.post(base + "/firms", json={"legal_name": "Deloitte Touche Tohmatsu India LLP", "short_name": "Deloitte"})
    ok(r.status_code == 201, "firm added")
    sub = data(c.get(base + "/participants"))["submissions"][0]["submission_id"]
    r = c.post(f"/api/v1/submissions/{sub}/file", files={"file": ("Deloitte all docs.pdf", open(BID,'rb').read(), "application/pdf")})
    ok(r.status_code == 201, "bid uploaded")
    part = data(c.get(base + "/participants"))
    ok(part["submissions"][0]["page_count"] == 464 and part["ready"] == 1 and part["approved"], "participant ready")
    elig = data(c.get(base + "/eligibility"))
    ok(elig["checking"] == 1 and elig["firms"][0]["status"] == "checking",
       "eligibility check queued on upload")
    ok(c.post(base + "/runs").status_code == 409, "no evaluation before a firm is qualified")
    ok(run_once(s, llm), "worker: check eligibility")
    firm = data(c.get(base + "/eligibility"))["firms"][0]
    ok(firm["status"] == "open" and firm["cells"][0]["result"] == "MET",
       "AI check awaits the committee")
    check = firm["cells"][0]["check_id"]
    ok(data(c.get(f"/api/v1/eligibility/{check}"))["check"]["pages"] == [1],
       "firm page with its proof page")
    decide = f"/api/v1/eligibility/{check}/decision"
    r = c.post(decide, json={"decision": "NOT_MET", "reason": "no"})
    ok(r.status_code == 400 and "disagree" in r.json()["message"], "disagreeing needs a reason")
    r = c.post(decide, json={"decision": "MET"})
    ok(r.status_code == 201, "confirming the AI needs no reason")
    ok(data(c.get(base + "/eligibility"))["qualified"] == 1, "firm qualified")
    r = c.post(base + "/runs"); ok(r.status_code == 201, "run started"); run = f"/api/v1/runs/{data(r)['run_id']}"
    ok(data(c.get(run))["rows"][0]["label"] == "Waiting to start", "progress page")
    ok(run_once(s, llm), "worker: evaluate Deloitte")
    ok(data(c.get(run))["run"]["status"] == "DONE", "run DONE")
    res = data(c.get(base + "/results"))
    ok(res["rows"][0]["name"] == "Deloitte" and any(x["code"] == "A.1" and x["max_marks"] == "16" for x in res["codes"])
       and res["committee"][0]["max_marks"] == "35", "results matrix")
    score = res["rows"][0]["cells"]["A.1"]["score_id"]
    ev = data(c.get(f"/api/v1/scores/{score}"))
    listed = [i for g in ev["groups"] for i in g["items"]]
    ok(any("Credential-1" in i["title"] for i in listed), "evidence page")
    img = c.get(f"/api/v1/submissions/{sub}/pages/143.png"); ok(img.status_code == 200 and img.content[:4] == b"\x89PNG", "page image")
    first = listed[0]["item_id"]
    r = c.post(f"/api/v1/scores/{score}/decision", json={"item_id": first, "action": "OVERRIDE", "marks": "0", "reason": "short"})
    ok(r.status_code == 400 and "at least 10" in r.json()["message"], "short reason refused")
    counted = [i["item_id"] for g in ev["groups"] if g["key"] == "counted" for i in g["items"]]
    for item_id in counted:                          # accepting needs no reason
        r = c.post(f"/api/v1/scores/{score}/decision", json={"item_id": item_id, "action": "ACCEPT"})
        ok(r.status_code == 201, "item decision recorded")
    pres = res["committee"][0]["criterion_id"]
    r = c.post(base + "/committee-marks", json={"marks": {pres: {sub: "32"}}}); ok(r.status_code == 200, "committee marks saved")
    res = data(c.get(base + "/results")); row = res["rows"][0]
    ok(row["cells"]["A.1"]["reviewed"] and row["manual"][pres] == "32",
       "results show the approved criterion + committee marks")
    ev = data(c.get(f"/api/v1/scores/{score}?item={counted[0]}"))
    ok(ev["item"]["decision"]["action"] == "ACCEPT", "item decision shown on the evidence page")

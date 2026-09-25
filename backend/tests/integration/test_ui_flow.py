"""End-to-end UI flow against a real, EMPTY test database, with a scripted LLM.

Needs: PostgreSQL (DB_* env pointing at a throw-away database; its public schema
is dropped and recreated), and the NSDF PDFs in data/golden/nsdf/.
Run: pytest -m integration
"""
import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.db.connection import transaction
from app.db.migrate import migrate
from app.jobs.worker import run_once
from app.llm.client import LlmClient
from app.web.app import create_app
from app.web.auth import hash_password

pytestmark = pytest.mark.integration
DATA = Path(__file__).resolve().parents[3] / "data" / "golden" / "nsdf"
RFP, BID = DATA / "RFP_Document_NSDF.pdf", DATA / "Deloitte all docs.pdf"
SECTIONS = [(75, 181, "A.1"), (182, 250, "A.2"), (251, 334, "A.3")]

def label(user):
    out = []
    for n, body in re.findall(r"\[PDF p\. (\d+)\]\n(.*?)(?=\n\n\[PDF p\. |\Z)", user, re.S):
        n = int(n); head = body.strip()[:200]
        code = next((c for a, b, c in SECTIONS if a <= n <= b), None)
        row = {"pdf_page_no": n, "page_type": "OTHER"}
        if re.search(r"Credential-\d+:", head) and code:
            row.update(page_type="PROJECT_HEADER", criterion_code=code, map_confidence=0.9, item_start=True)
        elif "Proposed CV for Program Manager" in head:
            row.update(page_type="CV", criterion_code="B.1", map_confidence=0.9, item_start=True)
        elif re.search(r"Proposed CV (of|for) Senior Consultant", head):
            row.update(page_type="CV", criterion_code="B.2", map_confidence=0.9, item_start=True)
        out.append(row)
    return json.dumps({"pages": out})

def item(user):
    code = re.search(r"Submitted under criterion: (\S+)", user).group(1)
    label_ = re.search(r"Item: (.+?) \(", user).group(1)
    first = re.search(r"\[PDF p\. (\d+)\]\n(.*?)\n", user, re.S)
    page, quote = int(first.group(1)), first.group(2).strip()[:60] or "x"
    marks = {"A.1": "2", "A.2": "2", "A.3": "2.5", "B.1": "8", "B.2": "7"}[code]
    return json.dumps({"label": label_, "code": code, "eligible": True, "marks": marks,
        "reason": "scripted", "confidence": 0.9, "relies_on": ["client"],
        "evidence": {"work_order": [page], "completion_or_ca": [page]},
        "facts": {"client": {"value": "c", "page": page, "quote": quote}}})

def criterion(user):
    mx = re.search(r"Max items: (\S+)\.", user).group(1); mx = int(mx) if mx.isdigit() else 99
    rows = json.loads(user.split("ITEM RESULTS\n", 1)[1])
    items = [dict(r, counted=i < mx) for i, r in enumerate(rows)]
    total = sum(float(r["marks"]) for r in items if r["counted"])
    return json.dumps({"code": re.search(r"criterion (\S+) for", user).group(1), "items": items,
                       "counted_items": min(len(rows), mx), "marks": str(total), "summary": "scripted"})


def fake(system, user):
    if "label pages" in system: return label(user)
    if "Submitted under criterion" in user: return item(user)
    return criterion(user)


GOLD = json.load(open(Path(__file__).resolve().parents[1] / 'golden/nsdf/criteria.json'))["criteria"]
def extraction(user):
    rows = [dict(code=c["code"], parent=c["code"][0], stage="TECHNICAL", title=c["title"],
                 rfp_text="[verbatim clause]", meaning=c["meaning"], max_marks=c["max_marks"],
                 max_items=c["max_items"], kind=c["kind"], item_marks=c["allowed_item_marks"],
                 scored_by="LLM", rfp_page=34) for c in GOLD]
    rows.append(dict(code="C", stage="PRESENTATION", title="Technical presentation", rfp_text="[clause]",
                     meaning="Presentation and interview", max_marks="35", scored_by="COMMITTEE"))
    rows.append(dict(code="E.1", stage="ELIGIBILITY", title="EMD", rfp_text="[clause]", meaning="EMD paid"))
    return json.dumps({"criteria": rows})
def fake_all(system, user):
    return extraction(user) if "extract evaluation criteria" in system else fake(system, user)


@pytest.mark.skipif(not (RFP.exists() and BID.exists()), reason="NSDF PDFs not in data/golden/nsdf")
def test_full_flow(tmp_path):
    root = tmp_path
    s = Settings(llm_cache_dir=str(root/'llm'), local_file_dir=str(root/'files'),
                 runs_dir=str(root/'runs'), session_secret='test-secret', cookie_secure=False,
                 ocr_engine='tesseract', ocr_min_chars=0, ocr_min_image_ratio=9)
    with transaction(s) as cur:
        cur.execute("drop schema public cascade; create schema public")
    migrate(s)
    with transaction(s) as cur:
        cur.execute("insert into app_user (email, full_name, role, password_hash) values (%s,%s,%s,%s)",
                    ("chair@dept.gov.in", "Committee Chair", "COMMITTEE", hash_password("correct horse battery")))
        cur.execute("insert into app_user (email, full_name, role, password_hash) values (%s,%s,%s,%s)",
                    ("viewer@dept.gov.in", "A Viewer", "VIEWER", hash_password("correct horse battery")))
    llm = LlmClient(s, completer=fake_all)
    app = create_app(s); c = TestClient(app, follow_redirects=False)
    def csrf(html): return re.search(r'name="csrf" value="([^"]+)"', html).group(1)
    def ok(cond, what): assert cond, what

    r = c.get("/projects"); ok(r.status_code == 303 and r.headers["location"] == "/login", "not logged in -> login")
    r = c.post("/login", data={"email": "chair@dept.gov.in", "password": "wrong"}); ok(r.status_code == 400, "bad password rejected")
    r = c.post("/login", data={"email": "chair@dept.gov.in", "password": "correct horse battery"}); ok(r.status_code == 303, "login")
    for h, v in [("content-security-policy", "default-src 'self'"), ("x-frame-options", "DENY")]:
        ok(v in r.headers.get(h, ""), f"header {h}")
    page = c.get("/projects").text; ok("No projects yet" in page, "empty projects list")
    tok = csrf(page)
    r = c.post("/projects", data={"name": "x", "due": "2026-05-07"}); ok(r.status_code == 403, "POST without CSRF refused")
    r = c.post("/projects", data={"csrf": tok, "name": "NSDF PMU 2026", "gem": "GEM/2026/B/7401395",
                                  "department": "Department of Sports, MYAS", "due": "2026-05-07"})
    ok(r.status_code == 303, "project created"); base = r.headers["location"].rsplit("/", 1)[0]
    r = c.post(base + "/rfp", data={"csrf": tok}, files={"file": ("notes.txt", b"hello", "text/plain")})
    ok("not a PDF" in r.text, "non-PDF upload rejected")
    r = c.post(base + "/rfp", data={"csrf": tok}, files={"file": ("RFP_Document_NSDF.pdf", open(RFP,'rb').read(), "application/pdf")})
    ok(r.status_code == 303, "RFP uploaded")
    ok("Reading the RFP" in c.get(base + "/criteria").text, "criteria page waits for worker")
    ok(run_once(s, llm), "worker: extract criteria")
    page = c.get(base + "/criteria").text
    ok("A.1" in page and "B.2" in page and "Committee only" in page, "criteria shown")
    r = c.post(base + "/criteria/approve", data={"csrf": tok}); ok(r.status_code == 303, "criteria approved")
    r = c.post(base.replace("/projects/", "/projects/") + "/firms", data={"csrf": tok, "legal_name": "Deloitte Touche Tohmatsu India LLP", "short_name": "Deloitte"})
    ok(r.status_code == 303, "firm added")
    page = c.get(base + "/participants").text; sub = re.search(r'/submissions/([0-9a-f-]{36})/file', page).group(1)
    r = c.post(f"/submissions/{sub}/file", data={"csrf": tok}, files={"file": ("Deloitte all docs.pdf", open(BID,'rb').read(), "application/pdf")})
    ok(r.status_code == 303, "bid uploaded")
    page = c.get(base + "/participants").text; ok("464 pages" in page and "Evaluate 1 participant" in page, "participant ready")
    r = c.post(base + "/runs", data={"csrf": tok}); ok(r.status_code == 303, "run started"); run_url = r.headers["location"]
    ok("Waiting to start" in c.get(run_url).text, "progress page")
    ok(run_once(s, llm), "worker: evaluate Deloitte")
    prog = c.get("/api/v1" + run_url + "/progress").json(); ok(prog["data"]["status"] == "DONE", f"progress api DONE ({prog['data']['status']})")
    page = c.get(run_url + "/results").text
    ok("Deloitte" in page and "A.1 /16" in page and "C presentation /35" in page, "results matrix")
    score = re.search(r'href="/scores/([0-9a-f-]{36})"', page).group(1)
    ev = c.get(f"/scores/{score}").text; ok("Credential-1" in ev and "Record decision" in ev, "evidence page")
    img = c.get(f"/submissions/{sub}/pages/143.png"); ok(img.status_code == 200 and img.content[:4] == b"\x89PNG", "page image")
    r = c.post(f"/scores/{score}/decision", data={"csrf": tok, "action": "OVERRIDE", "marks": "12", "reason": "short"}); ok("at least 10" in r.text, "short reason refused")
    r = c.post(f"/scores/{score}/decision", data={"csrf": tok, "action": "OVERRIDE", "marks": "12", "reason": "Credentials 7-11 fail duration, India-only and award-date rules"}); ok(r.status_code == 303, "decision recorded")
    r = c.post(run_url + "/presentation", data={"csrf": tok, f"p_{sub}": "32"}); ok(r.status_code == 303, "presentation saved")
    page = c.get(run_url + "/results").text; ok(">12<" in page.replace("● ", "") and "decided" in page and 'value="32' in page, "results show decision + presentation")
    c.post("/logout", data={"csrf": tok})
    c.post("/login", data={"email": "viewer@dept.gov.in", "password": "correct horse battery"})
    ok(c.get(f"/scores/{score}").status_code == 403, "viewer cannot open evidence")
    ok(c.get(f"/submissions/{sub}/pages/1.png").status_code == 403, "viewer cannot see bid pages")
    ok(c.get("/projects").status_code == 200, "viewer sees projects")

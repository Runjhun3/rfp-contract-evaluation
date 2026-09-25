"""End-to-end API flow (what the React UI calls) against a real, EMPTY test database,
with a scripted LLM.

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
                 runs_dir=str(root/'runs'),
                 ocr_engine='tesseract', ocr_min_chars=0, ocr_min_image_ratio=9)
    with transaction(s) as cur:
        cur.execute("drop schema public cascade; create schema public")
    migrate(s)
    llm = LlmClient(s, completer=fake_all)
    c = TestClient(create_app(s), follow_redirects=False)
    def ok(cond, what): assert cond, what
    def data(r): return r.json()["data"]

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
    r = c.post(base + "/runs"); ok(r.status_code == 201, "run started"); run = f"/api/v1/runs/{data(r)['run_id']}"
    ok(data(c.get(run))["rows"][0]["label"] == "Waiting to start", "progress page")
    ok(run_once(s, llm), "worker: evaluate Deloitte")
    ok(data(c.get(run))["run"]["status"] == "DONE", "run DONE")
    res = data(c.get(run + "/results"))
    ok(res["rows"][0]["name"] == "Deloitte" and any(x["code"] == "A.1" and x["max_marks"] == "16" for x in res["codes"])
       and res["presentation"]["max_marks"] == "35", "results matrix")
    score = res["rows"][0]["cells"]["A.1"]["score_id"]
    ev = data(c.get(f"/api/v1/scores/{score}"))
    ok(any("Credential-1" in (i["title"] or i["label"]) for i in ev["items"]), "evidence page")
    img = c.get(f"/api/v1/submissions/{sub}/pages/143.png"); ok(img.status_code == 200 and img.content[:4] == b"\x89PNG", "page image")
    r = c.post(f"/api/v1/scores/{score}/decision", json={"action": "OVERRIDE", "marks": "12", "reason": "short"})
    ok(r.status_code == 400 and "at least 10" in r.json()["message"], "short reason refused")
    r = c.post(f"/api/v1/scores/{score}/decision", json={"action": "OVERRIDE", "marks": "12", "reason": "Credentials 7-11 fail duration, India-only and award-date rules"})
    ok(r.status_code == 201, "decision recorded")
    r = c.post(run + "/presentation", json={"marks": {sub: "32"}}); ok(r.status_code == 200, "presentation saved")
    res = data(c.get(run + "/results")); row = res["rows"][0]
    ok(row["cells"]["A.1"]["marks"] == "12" and row["cells"]["A.1"]["reviewed"] and row["presentation"] == "32",
       "results show decision + presentation")
    ok(data(c.get(f"/api/v1/scores/{score}"))["history"][0]["full_name"] == "Local user",
       "decision recorded against the built-in local user")

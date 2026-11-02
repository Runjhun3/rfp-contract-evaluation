"""Named accounts and the on-screen audit trail, through the API, against a real EMPTY
test database. No PDFs or AWS needed: criteria are inserted directly and the LLM always
fails.

Needs: PostgreSQL (DB_* env pointing at a throw-away database; its public schema
is dropped and recreated). Run: pytest -m integration
"""
import io

import pypdfium2 as pdfium
import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.db.connection import transaction
from app.db.migrate import migrate
from app.jobs.worker import run_once
from app.llm.client import LlmClient
from app.web.app import create_app

pytestmark = pytest.mark.integration


def _pdf() -> bytes:
    doc = pdfium.PdfDocument.new()
    doc.new_page(595, 842)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _no_llm(system, user, images):
    raise RuntimeError("no LLM in this test")


def _client(s: Settings, username: str, password: str) -> TestClient:
    c = TestClient(create_app(s), follow_redirects=False)
    c.headers["X-CSRF-Token"] = c.get("/api/v1/session").json()["data"]["csrf"]
    r = c.post("/api/v1/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.json()
    c.headers["X-CSRF-Token"] = r.json()["data"]["csrf"]
    return c


def test_accounts_and_audit_trail(tmp_path):
    s = Settings(llm_cache_dir=str(tmp_path / "llm"), local_file_dir=str(tmp_path / "files"),
                 runs_dir=str(tmp_path / "runs"), ocr_engine="tesseract", ocr_min_chars=0,
                 ocr_min_image_ratio=9, app_username="admin", app_password="admin-pass-1")
    with transaction(s) as cur:
        cur.execute("drop schema public cascade; create schema public")
    migrate(s)
    admin = _client(s, "admin", "admin-pass-1")
    assert admin.get("/api/v1/session").json()["data"]["role"] == "ADMIN"

    new = {"username": "Asha", "full_name": "Asha Rao", "role": "COMMITTEE",
           "password": "asha-password-1"}
    assert admin.post("/api/v1/users", json={**new, "password": "short"}).status_code == 400
    assert admin.post("/api/v1/users", json={**new, "username": "ADMIN"}).status_code == 400
    assert admin.post("/api/v1/users", json=new).status_code == 201
    listed = admin.get("/api/v1/users").json()["data"]
    asha_id = listed["users"][0]["user_id"]
    assert [u["username"] for u in listed["users"]] == ["asha"]       # .env account not listed
    assert listed["events"][0]["what"] == "Account created"

    asha = _client(s, "asha", "asha-password-1")
    assert asha.get("/api/v1/users").status_code == 403         # not an administrator
    r = asha.post("/api/v1/projects", json={"name": "Audit test", "due": "2026-05-07"})
    base = f"/api/v1/projects/{r.json()['data']['tender_id']}"
    assert asha.post(base + "/rfp", files={"file": ("rfp.pdf", _pdf(), "application/pdf")}).status_code == 201
    assert run_once(s, LlmClient(s, completer=_no_llm))          # reading the RFP fails
    firm = asha.post(base + "/firms", json={"legal_name": "Ernst & Young LLP", "short_name": "EY"})
    assert firm.status_code == 201
    assert asha.post(base + "/participants", json={"bidder_ids": []}).status_code == 200

    assert asha.get(base + "/audit").status_code == 403         # activity log: admins only
    assert asha.get(base + "/decisions").json()["data"]["firms"] == []   # nothing decided yet
    trail = admin.get(base + "/audit").json()["data"]
    done = [(r["who"], r["what"], r["details"]) for r in reversed(trail["rows"])]   # oldest first
    assert done[:2] == [("Asha Rao", "Project created", "Audit test"),
                        ("Asha Rao", "RFP uploaded", "rfp.pdf")], done   # no AI or worker rows
    assert sorted(done[2:4]) == [("Asha Rao", "Firm added", "EY · Ernst & Young LLP"),
                                 ("Asha Rao", "Participant added", "EY")]   # same transaction
    assert done[4:] == [("Asha Rao", "Participant removed", "EY")]
    only = admin.get(base + "/audit?category=PROJECT").json()["data"]
    assert only["category"] == "PROJECT" and len(only["rows"]) == 2 and only["pages"] == 1
    central = admin.get("/api/v1/activity?category=SIGN_IN").json()["data"]["rows"]
    assert [(r["who"], r["what"]) for r in reversed(central)] == [
        ("admin", "Signed in"), ("Asha Rao", "Signed in")]
    assert asha.get("/api/v1/activity").status_code == 403
    assert asha.get("/api/v1/activity.csv").status_code == 403

    # Filters: one person, a date range (both days included; a bad date is ignored).
    mine = admin.get(f"/api/v1/activity?who={asha_id}").json()["data"]
    assert mine["who"] == asha_id and {r["who"] for r in mine["rows"]} == {"Asha Rao"}
    today = admin.get("/api/v1/activity?since=2000-01-01&until=2999-12-31").json()["data"]
    assert today["total"] > 0 and today["since"] == "2000-01-01"
    assert admin.get("/api/v1/activity?until=2000-01-01").json()["data"]["total"] == 0
    assert admin.get("/api/v1/activity?since=31/12/2026").json()["data"]["since"] is None
    assert any(p["name"] == "Asha Rao" for p in mine["people"])

    # CSV: every matching row, as a file; the download itself goes on the log.
    csv = admin.get(f"/api/v1/activity.csv?category=SIGN_IN&who={asha_id}")
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert 'filename="activity-log-all-projects-' in csv.headers["content-disposition"]
    lines = csv.content.decode("utf-8-sig").splitlines()
    assert lines[0] == "Date & time,Who,Area,What,Project,Details" and len(lines) == 2
    assert ",Asha Rao,Sign-in,Signed in," in lines[1]
    project_csv = admin.get(base + "/audit.csv")
    assert 'filename="activity-log-Audit-test-' in project_csv.headers["content-disposition"]
    exports = admin.get("/api/v1/activity?category=EXPORTS").json()["data"]["rows"]
    assert [(r["who"], r["what"]) for r in exports] == [
        ("admin", "Activity log downloaded"), ("admin", "Activity log downloaded")]
    assert admin.get(base + "/audit?category=EXPORTS").json()["data"]["total"] == 1

    assert admin.post(f"/api/v1/users/{asha_id}/active", json={"active": False}).status_code == 200
    assert asha.get(base + "/decisions").status_code == 401         # signed out at once
    admin.post(f"/api/v1/users/{asha_id}/active", json={"active": True})
    admin.post(f"/api/v1/users/{asha_id}/password", json={"password": "a-new-password-2"})
    _client(s, "asha", "a-new-password-2")
    kinds = [(e["what"], e["code"]) for e in admin.get("/api/v1/users").json()["data"]["events"]]
    assert kinds[:3] == [("Password set", "asha"), ("Account switched on", "asha"),
                         ("Account switched off", "asha")]

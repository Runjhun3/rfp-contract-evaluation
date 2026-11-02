from contextlib import contextmanager

import pytest

from app import users
from app.db import q_events
from app.passwords import hash_password, verify_password


def test_passwords_are_salted_and_checked_in_constant_time():
    stored = hash_password("correct horse battery")
    assert stored.startswith("scrypt$") and stored != hash_password("correct horse battery")
    assert verify_password("correct horse battery", stored)
    assert not verify_password("wrong horse battery", stored)
    assert not verify_password("anything", None) and not verify_password("x", "garbage$$")


@pytest.fixture
def events(monkeypatch):
    added = []
    monkeypatch.setattr(users.q_events, "add", lambda cur, *event: added.append(event))
    return added


@pytest.fixture
def accounts(monkeypatch):
    rows = {"u1": {"user_id": "u1", "username": "asha", "full_name": "Asha Rao",
                   "role": "COMMITTEE", "is_active": True, "named": True,
                   "password_hash": hash_password("asha-password-1")},
            "env": {"user_id": "env", "username": "admin", "full_name": "admin",
                    "role": "ADMIN", "is_active": True, "named": False, "password_hash": None}}
    by_name = {r["username"]: r for r in rows.values()}
    monkeypatch.setattr(users.q_users, "by_username", lambda cur, n: by_name.get(n.lower()))
    monkeypatch.setattr(users.q_users, "get", lambda cur, uid: rows.get(uid))
    monkeypatch.setattr(users.q_users, "create", lambda cur, *a: "u2")
    monkeypatch.setattr(users.q_users, "set_active",
                        lambda cur, uid, on: rows[uid].update(is_active=on))
    monkeypatch.setattr(users.q_users, "set_password", lambda cur, uid, h: None)
    return rows


def test_only_an_active_named_account_with_the_right_password_signs_in(accounts):
    assert users.authenticate(None, "asha", "asha-password-1")["role"] == "COMMITTEE"
    assert users.authenticate(None, "asha", "wrong-password") is None
    assert users.authenticate(None, "nobody", "asha-password-1") is None
    assert users.authenticate(None, "admin", "") is None          # the .env row has no hash
    accounts["u1"]["is_active"] = False
    assert users.authenticate(None, "asha", "asha-password-1") is None


def test_a_new_account_needs_a_free_username_a_name_a_role_and_a_long_password(accounts,
                                                                                events):
    good = {"username": "Ravi.K", "full_name": "  Ravi   Kumar ", "role": "ADMIN",
            "password": "long-enough-pass"}
    assert "username of 3 to 40" in users.create(None, {**good, "username": "r!"}, "a", "boss")
    assert users.create(None, {**good, "username": "asha"}, "a", "boss") == (
        "That username is already taken.")
    assert users.create(None, {**good, "username": "BOSS"}, "a", "boss") == (
        "That username is already taken.")                  # the .env account's name
    assert users.create(None, {**good, "role": "OWNER"}, "a", "boss") == "Choose a role."
    assert "at least 12" in users.create(None, {**good, "password": "short"}, "a", "boss")
    assert users.create(None, good, "a", "boss") is None
    assert events == [(None, "a", "Account created", "ravi.k",
                       {"note": "Ravi Kumar · administrator"})]
    assert "long-enough-pass" not in str(events)                # never on the record


def test_only_named_accounts_are_managed_and_nobody_switches_off_themself(accounts, events):
    assert users.set_active(None, "u1", False, "u1") == "You cannot switch off your own account."
    assert users.set_active(None, "u1", False, "env") is None
    assert not accounts["u1"]["is_active"]
    assert events == [(None, "env", "Account switched off", "asha", {})]
    assert users.set_active(None, "env", False, "u1") == users.NOT_FOUND   # the .env account
    assert users.reset_password(None, "zz", "long-enough-pass", "env") == users.NOT_FOUND


def test_each_failed_job_attempt_is_an_event_by_the_system(monkeypatch):
    added = []
    monkeypatch.setattr(q_events, "add", lambda cur, *event: added.append(event))
    monkeypatch.setattr(q_events, "one_row", lambda cur, sql, args: {"short_name": "EY"})
    job = {"job_id": 7, "kind": "EVALUATE_SUBMISSION", "ref_id": "s1", "tender_id": "t",
           "attempts": 1}
    q_events.job_failed(None, job, "ThrottlingException: slow down", 3)
    q_events.job_failed(None, {**job, "attempts": 3}, "ThrottlingException: slow down", 3)
    assert [(e[0], e[1], e[2], e[3]) for e in added] == [
        ("t", None, "Evaluate Submission · attempt 1 of 3 failed, will retry", "EY"),
        ("t", None, "Evaluate Submission · attempt 3 of 3 failed", "EY")]
    assert added[0][4] == {"note": "ThrottlingException: slow down", "job_id": 7}


def _login_app(monkeypatch, account):
    from types import SimpleNamespace

    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app.web import auth, routes_auth

    @contextmanager
    def no_db(settings):
        yield None

    monkeypatch.setattr(routes_auth, "transaction", no_db)
    monkeypatch.setattr(auth, "transaction", no_db)
    monkeypatch.setattr(routes_auth, "authenticate", lambda cur, n, p: (
        {"user_id": "u1", "name": "Asha Rao", "role": "COMMITTEE"}
        if (n, p) == ("asha", "asha-password-1") else None))
    monkeypatch.setattr(auth.q_users, "get", lambda cur, uid: account)
    monkeypatch.setattr(routes_auth.q_events, "add", lambda cur, *event: None)

    async def projects(request):
        return JSONResponse({"data": auth.current_user(request), "message": "ok"})

    app = Starlette(routes=[*routes_auth.routes, Route("/api/v1/projects", projects)],
                    middleware=[Middleware(SessionMiddleware, secret_key="test"),
                                Middleware(auth.RequireLogin)])
    app.state.settings = SimpleNamespace(app_username="adminuser", app_password="s3cret!")
    return app


def test_a_named_account_acts_as_itself_until_it_is_switched_off(monkeypatch):
    from starlette.testclient import TestClient

    account = {"user_id": "u1", "role": "COMMITTEE", "is_active": True}
    c = TestClient(_login_app(monkeypatch, account))
    token = c.get("/api/v1/session").json()["data"]["csrf"]
    reply = c.post("/api/v1/login", json={"username": "Asha", "password": "asha-password-1"},
                   headers={"X-CSRF-Token": token}).json()["data"]
    assert reply["user"] == "Asha Rao" and reply["role"] == "COMMITTEE"
    assert c.get("/api/v1/projects").json()["data"] == "u1"       # recorded as Asha
    account["is_active"] = False
    assert c.get("/api/v1/projects").status_code == 401
    assert c.get("/api/v1/session").json()["data"]["user"] is None

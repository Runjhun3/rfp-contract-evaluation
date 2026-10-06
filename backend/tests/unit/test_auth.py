from contextlib import contextmanager
from types import SimpleNamespace

from app.web.auth import credentials_ok, current_user, needs_login


def test_only_the_configured_account_signs_in():
    assert credentials_ok("adminuser", "s3cret!", "adminuser", "s3cret!")
    assert not credentials_ok("adminuser", "wrong", "adminuser", "s3cret!")
    assert not credentials_ok("admin", "s3cret!", "adminuser", "s3cret!")


def test_an_unset_account_never_signs_anyone_in():
    assert not credentials_ok("", "", "", "")
    assert not credentials_ok("adminuser", "", "adminuser", "")


def test_every_api_call_needs_a_session_except_session_and_login():
    assert needs_login("/api/v1/projects") and needs_login("/api/v1/logout")
    assert not needs_login("/api/v1/session") and not needs_login("/api/v1/login")
    assert not needs_login("/login") and not needs_login("/assets/app.js")


def _app(monkeypatch, username="adminuser", password="s3cret!"):
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app.web import routes_auth
    from app.web.auth import RequireLogin

    @contextmanager
    def no_db(settings):
        yield None
    monkeypatch.setattr(routes_auth, "transaction", no_db)
    monkeypatch.setattr(routes_auth.q_users, "account", lambda cur, name: f"id-of-{name}")

    async def projects(request):
        return JSONResponse({"data": [], "message": "ok"})

    app = Starlette(routes=[*routes_auth.routes, Route("/api/v1/projects", projects)],
                    middleware=[Middleware(SessionMiddleware, secret_key="test"),
                                Middleware(RequireLogin)])
    app.state.settings = SimpleNamespace(app_username=username, app_password=password)
    return app


def test_sign_in_opens_the_api_and_sign_out_closes_it(monkeypatch):
    from starlette.testclient import TestClient

    c = TestClient(_app(monkeypatch))
    assert c.get("/api/v1/projects").status_code == 401
    token = c.get("/api/v1/session").json()["data"]["csrf"]
    assert c.post("/api/v1/login", json={"username": "adminuser", "password": "nope"},
                  headers={"X-CSRF-Token": token}).status_code == 401
    ok = c.post("/api/v1/login", json={"username": "adminuser", "password": "s3cret!"},
                headers={"X-CSRF-Token": token}).json()["data"]
    assert ok["user"] == "adminuser" and ok["csrf"] != token          # new session on sign-in
    assert c.get("/api/v1/projects").status_code == 200
    c.post("/api/v1/logout", headers={"X-CSRF-Token": ok["csrf"]})
    assert c.get("/api/v1/projects").status_code == 401


def test_sign_in_is_refused_until_the_account_is_set(monkeypatch):
    from starlette.testclient import TestClient

    c = TestClient(_app(monkeypatch, password=""))
    token = c.get("/api/v1/session").json()["data"]["csrf"]
    reply = c.post("/api/v1/login", json={"username": "adminuser", "password": ""},
                   headers={"X-CSRF-Token": token})
    assert reply.status_code == 503


def test_actions_are_recorded_against_the_signed_in_account():
    assert current_user(SimpleNamespace(session={"user_id": "u-7"})) == "u-7"
    # A session signed in before accounts were recorded: the built-in local user.
    assert current_user(SimpleNamespace(session={})).startswith("00000000-")

"""API: the session, sign in and sign out (see app/web/auth.py)."""
import asyncio
import secrets

from starlette.routing import Route

from app.db import q_events, q_users
from app.db.connection import transaction
from app.users import ROLES, authenticate
from app.web.auth import check_csrf, credentials_ok, csrf_token
from app.web.common import fail, ok

WRONG = "Wrong username or password."
NOT_SET = "Sign-in is not set up: add APP_USERNAME and APP_PASSWORD to .env and restart."


async def session(request):
    user = request.session.get("user")
    return ok({"csrf": csrf_token(request), "user": user,
               "role": request.session.get("role", "ADMIN") if user else None})


def _account(settings, username: str, password: str) -> dict | str | None:
    """The account signing in: the .env administrator or a named account. NOT_SET when
    it is the .env account and that is not set up."""
    if username and username == settings.app_username:      # the built-in administrator
        if not settings.app_password:
            return NOT_SET
        if not credentials_ok(username, password, settings.app_username, settings.app_password):
            return None
        with transaction(settings) as cur:
            user_id = q_users.account(cur, username)
            if user_id:                                       # on the activity log
                q_events.add(cur, None, user_id, "Signed in", username,
                             {"note": "built-in administrator"})
        return user_id and {"user_id": user_id, "name": username, "role": "ADMIN",
                            "named": False}
    if not username or not password:
        return None
    with transaction(settings) as cur:
        account = authenticate(cur, username.lower(), password)
        if account:
            q_events.add(cur, None, account["user_id"], "Signed in", username.lower(),
                         {"note": ROLES[account["role"]].lower()})
    return account and {**account, "named": True}


async def login(request):
    check_csrf(request)
    body = await request.json()
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    account = _account(request.app.state.settings, username, password)
    if account == NOT_SET:
        return fail(NOT_SET, 503)
    if not account:
        await asyncio.sleep(1)          # slows password guessing
        return fail(WRONG, 401)
    request.session.clear()             # new session on sign-in: no fixation
    request.session.update(user=account["name"], user_id=account["user_id"],
                           role=account["role"], named=account["named"],
                           csrf=secrets.token_urlsafe(24))
    return ok({"csrf": request.session["csrf"], "user": account["name"],
               "role": account["role"]}, "Signed in")


async def logout(request):
    check_csrf(request)
    user_id, name = request.session.get("user_id"), request.session.get("user")
    if user_id and name:
        with transaction(request.app.state.settings) as cur:
            q_events.add(cur, None, user_id, "Signed out", name, {})
    request.session.clear()
    return ok(None, "Signed out")


routes = [
    Route("/api/v1/session", session, methods=["GET"]),
    Route("/api/v1/login", login, methods=["POST"]),
    Route("/api/v1/logout", logout, methods=["POST"]),
]

"""API: the session, sign in and sign out (see app/web/auth.py)."""
import asyncio
import secrets

from starlette.routing import Route

from app.web.auth import check_csrf, credentials_ok, csrf_token
from app.web.common import fail, ok

WRONG = "Wrong username or password."
NOT_SET = "Sign-in is not set up: add APP_USERNAME and APP_PASSWORD to .env and restart."


async def session(request):
    return ok({"csrf": csrf_token(request), "user": request.session.get("user")})


async def login(request):
    check_csrf(request)
    settings = request.app.state.settings
    if not settings.app_username or not settings.app_password:
        return fail(NOT_SET, 503)
    body = await request.json()
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    if not credentials_ok(username, password, settings.app_username, settings.app_password):
        await asyncio.sleep(1)          # slows password guessing
        return fail(WRONG, 401)
    request.session.clear()             # new session on sign-in: no fixation
    request.session.update(user=username, csrf=secrets.token_urlsafe(24))
    return ok({"csrf": request.session["csrf"], "user": username}, "Signed in")


async def logout(request):
    check_csrf(request)
    request.session.clear()
    return ok(None, "Signed out")


routes = [
    Route("/api/v1/session", session, methods=["GET"]),
    Route("/api/v1/login", login, methods=["POST"]),
    Route("/api/v1/logout", logout, methods=["POST"]),
]

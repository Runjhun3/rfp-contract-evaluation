"""Sign-in: one account from .env (APP_USERNAME / APP_PASSWORD; decisions.md D-042).

Every /api/ call needs a signed-in session except the ones in PUBLIC; RequireLogin
answers 401 otherwise. Every write (POST) must also carry the session's CSRF token
in the X-CSRF-Token header, so another site cannot act from the user's browser.
Actions are recorded against the signed-in account's app_user row (current_user).
"""
import hmac
import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db.repo_setup import LOCAL_USER_ID

CSRF_HEADER = "x-csrf-token"
PUBLIC = {"/api/v1/session", "/api/v1/login"}


class Forbidden(Exception):
    pass


def csrf_token(request: Request) -> str:
    """The session's CSRF token, created on first use."""
    return request.session.setdefault("csrf", secrets.token_urlsafe(24))


def check_csrf(request: Request) -> None:
    expected = request.session.get("csrf", "")
    sent = request.headers.get(CSRF_HEADER, "")
    if not expected or not hmac.compare_digest(sent, expected):
        raise Forbidden()


def current_user(request: Request) -> str:
    """Who is acting: the signed-in account's user id. A session signed in before
    accounts were recorded falls back to the built-in local user."""
    return request.session.get("user_id") or LOCAL_USER_ID


def credentials_ok(username: str, password: str, want_user: str, want_password: str) -> bool:
    """Constant-time check. An unset account (empty password) never signs anyone in."""
    if not want_user or not want_password:
        return False
    user_ok = hmac.compare_digest(username.encode(), want_user.encode())
    password_ok = hmac.compare_digest(password.encode(), want_password.encode())
    return user_ok and password_ok


def needs_login(path: str) -> bool:
    return path.startswith("/api/") and path not in PUBLIC


class RequireLogin:
    """ASGI middleware; must sit inside SessionMiddleware so scope["session"] exists."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] == "http" and needs_login(scope["path"])
                and not scope.get("session", {}).get("user")):
            reply = JSONResponse({"data": None, "message": "Please sign in."}, status_code=401)
            await reply(scope, receive, send)
            return
        await self.app(scope, receive, send)

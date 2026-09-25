"""No login: the app runs as one built-in local user (migration 002_local_user).

Anyone who can reach the URL can do everything, so run it only on localhost or a
private network. Every write (POST) must carry the session's CSRF token in the
X-CSRF-Token header, so another site cannot act from the user's browser.
"""
import hmac
import secrets

from starlette.requests import Request

CSRF_HEADER = "x-csrf-token"


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

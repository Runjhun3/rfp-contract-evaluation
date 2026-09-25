"""No login: the app runs as one built-in local user (migration 002_local_user).

Anyone who can reach the URL can do everything, so run it only on localhost or a
private network. Every POST still checks a CSRF token so another site cannot
submit forms here from the user's browser.
"""
import hmac
import secrets

from starlette.requests import Request

from app.db.repo_setup import LOCAL_USER_ID

LOCAL_USER = {"user_id": LOCAL_USER_ID, "full_name": "Local user"}


class Forbidden(Exception):
    pass


def local_user(request: Request) -> dict:
    """The user every action is recorded against. Also starts the CSRF session."""
    request.session.setdefault("csrf", secrets.token_urlsafe(24))
    return dict(LOCAL_USER)


async def form_with_csrf(request: Request):
    form = await request.form()
    expected = request.session.get("csrf", "")
    if not expected or not hmac.compare_digest(str(form.get("csrf", "")), expected):
        raise Forbidden()
    return form

"""Login, roles and CSRF. Local accounts (scrypt) until SSO is chosen.

Roles nest: VIEWER < EVALUATOR < COMMITTEE < ADMIN. Every POST and every page
that shows bid content checks the role on the server; hiding a button in the
template is only for convenience.
"""
import hashlib
import hmac
import secrets

from starlette.requests import Request

from app.db import q_projects
from app.db.connection import transaction

LEVEL = {"VIEWER": 0, "EVALUATOR": 1, "COMMITTEE": 2, "ADMIN": 3}


class NotLoggedIn(Exception):
    pass


class Forbidden(Exception):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        _, salt, digest = (stored or "").split("$")
    except ValueError:
        return False
    test = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1)
    return hmac.compare_digest(test.hex(), digest)


def login(request: Request, user_id: str) -> None:
    request.session.clear()
    request.session.update({"uid": user_id, "csrf": secrets.token_urlsafe(24)})


def current_user(request: Request) -> dict | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    with transaction(request.app.state.settings) as cur:
        return q_projects.user_by_id(cur, uid)


def need(request: Request, role: str = "VIEWER") -> dict:
    user = current_user(request)
    if user is None:
        raise NotLoggedIn()
    if LEVEL[user["role"]] < LEVEL[role]:
        raise Forbidden()
    user["can_edit"] = LEVEL[user["role"]] >= LEVEL["EVALUATOR"]
    user["can_decide"] = LEVEL[user["role"]] >= LEVEL["COMMITTEE"]
    return user


async def form_with_csrf(request: Request):
    form = await request.form()
    expected = request.session.get("csrf", "")
    if not expected or not hmac.compare_digest(str(form.get("csrf", "")), expected):
        raise Forbidden()
    return form

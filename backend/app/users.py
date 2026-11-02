"""Named sign-in accounts (docs/decisions.md, D-056). An administrator creates them, switches
them off and on again, and sets a new password; each change is an audit event (no
project, so it never shows in a project's history). Accounts are never deleted:
decisions and the audit trail point at them.

The .env account (APP_USERNAME / APP_PASSWORD) is the built-in administrator. Its
sign-in name is reserved, and it is not listed or managed here.
"""
import re
from functools import lru_cache

from app.db import q_events, q_users
from app.passwords import hash_password, password_problem, verify_password

ROLES = {"ADMIN": "Administrator", "COMMITTEE": "Committee member"}
USERNAME = re.compile(r"[a-z0-9][a-z0-9._@-]{2,39}")
NOT_FOUND = "Account not found"


@lru_cache
def _dummy_hash() -> str:
    """Checked when no account matches, so a wrong username takes as long as a wrong password."""
    return hash_password("no account has this password")


def authenticate(cur, username: str, password: str) -> dict | None:
    """The active named account with this username and password, else None."""
    account = q_users.by_username(cur, username) if username and password else None
    stored = account["password_hash"] if account else None
    ok = verify_password(password, stored or _dummy_hash())
    if not (account and stored and ok and account["is_active"]):
        return None
    return {"user_id": account["user_id"], "name": account["full_name"],
            "role": account["role"]}


def create(cur, body: dict, actor: str, reserved: str) -> str | None:
    """Create an account from {username, full_name, role, password}. None when created,
    else why not."""
    username = str(body.get("username") or "").strip().lower()
    full_name = " ".join(str(body.get("full_name") or "").split())
    role, password = str(body.get("role") or ""), str(body.get("password") or "")
    if not USERNAME.fullmatch(username):
        return ("Choose a username of 3 to 40 characters: letters, digits and . _ - @, "
                "starting with a letter or digit.")
    if username == reserved.strip().lower() or q_users.by_username(cur, username):
        return "That username is already taken."
    if not 1 <= len(full_name) <= 100:
        return "Enter the person's full name (up to 100 characters)."
    if role not in ROLES:
        return "Choose a role."
    problem = password_problem(password)
    if problem:
        return problem
    q_users.create(cur, username, full_name, role, hash_password(password), actor)
    q_events.add(cur, None, actor, "Account created", username,
                 {"note": f"{full_name} · {ROLES[role].lower()}"})
    return None


def _named(cur, user_id: str) -> dict | None:
    account = q_users.get(cur, user_id)
    return account if account and account["named"] else None


def set_active(cur, user_id: str, active: bool, actor: str) -> str | None:
    account = _named(cur, user_id)
    if account is None:
        return NOT_FOUND
    if user_id == actor and not active:
        return "You cannot switch off your own account."
    if account["is_active"] == active:
        return None
    q_users.set_active(cur, user_id, active)
    q_events.add(cur, None, actor, "Account switched on" if active else "Account switched off",
                 account["username"], {})
    return None


def reset_password(cur, user_id: str, password: str, actor: str) -> str | None:
    account = _named(cur, user_id)
    if account is None:
        return NOT_FOUND
    problem = password_problem(password)
    if problem:
        return problem
    q_users.set_password(cur, user_id, hash_password(password))
    q_events.add(cur, None, actor, "Password set", account["username"], {})
    return None


def overview(cur) -> dict:
    """The accounts screen: every named account and the latest account changes."""
    return {"users": [{**u, "role_label": ROLES.get(u["role"], u["role"])}
                      for u in q_users.list_users(cur)],
            "roles": [{"key": k, "label": v} for k, v in ROLES.items()],
            "events": q_events.account_history(cur)}

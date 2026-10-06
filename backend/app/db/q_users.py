"""Queries for the people actions are recorded against (app_user)."""
from app.db.connection import one_row


def account(cur, username: str) -> str:
    """The app_user row of a signed-in account, created on its first sign-in, so the
    audit trail names who acted. Its email column holds the sign-in name."""
    return one_row(cur, """insert into app_user (email, full_name, role)
                           values (%s, %s, 'ADMIN')
                           on conflict (email) do update set full_name = app_user.full_name
                           returning user_id::text""", (username, username))["user_id"]

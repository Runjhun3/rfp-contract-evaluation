"""Queries for the people actions are recorded against (app_user). The sign-in name is
kept in the email column: the .env account's (created on its first sign-in) and each
named account's (created by an administrator, with a password hash; migration 018)."""
from app.db.connection import all_rows, one_row

_FIELDS = """u.user_id::text, u.email as username, u.full_name, u.role, u.is_active,
             to_char(u.created_at, 'DD Mon YYYY HH24:MI') as created,
             (select c.full_name from app_user c where c.user_id = u.created_by) as created_by"""


def account(cur, username: str) -> str | None:
    """The app_user row of the .env account, created on its first sign-in, so the
    audit trail names who acted. None when a named account already has that name: the
    .env account never acts as someone else."""
    row = one_row(cur, "select user_id::text, password_hash from app_user "
                       "where lower(email) = lower(%s)", (username,))
    if row:
        return None if row["password_hash"] else row["user_id"]
    return one_row(cur, """insert into app_user (email, full_name, role)
                           values (%s, %s, 'ADMIN') returning user_id::text""",
                   (username, username))["user_id"]


def by_username(cur, username: str) -> dict | None:
    """Any account with this sign-in name, with its password hash (never sent out)."""
    return one_row(cur, f"""select {_FIELDS}, u.password_hash from app_user u
                            where lower(u.email) = lower(%s)""", (username,))


def get(cur, user_id: str) -> dict | None:
    return one_row(cur, f"""select {_FIELDS}, u.password_hash is not null as named
                            from app_user u where u.user_id = %s""", (user_id,))


def list_users(cur) -> list[dict]:
    """Every named account (those with a password), active first."""
    return all_rows(cur, f"""select {_FIELDS} from app_user u where u.password_hash is not null
                             order by u.is_active desc, lower(u.email)""")


def create(cur, username: str, full_name: str, role: str, password_hash: str,
           created_by: str) -> str:
    row = one_row(cur, """insert into app_user (email, full_name, role, password_hash,
                            created_by) values (%s, %s, %s, %s, %s) returning user_id::text""",
                  (username, full_name, role, password_hash, created_by))
    return row["user_id"]


def set_active(cur, user_id: str, active: bool) -> None:
    cur.execute("update app_user set is_active = %s where user_id = %s", (active, user_id))


def set_password(cur, user_id: str, password_hash: str) -> None:
    cur.execute("update app_user set password_hash = %s where user_id = %s",
                (password_hash, user_id))

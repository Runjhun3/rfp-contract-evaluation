"""Postgres connection (psycopg 3). One short transaction per unit of work."""
from contextlib import contextmanager
from typing import Iterator

from app.config import Settings


@contextmanager
def transaction(settings: Settings) -> Iterator[object]:
    """Yields a cursor; commits on success, rolls back on any error."""
    import psycopg

    with psycopg.connect(settings.db_conninfo()) as conn:
        with conn.cursor() as cur:
            yield cur


def all_rows(cur, sql: str, params: tuple = ()) -> list[dict]:
    cur.execute(sql, params)
    rows = cur.fetchall()
    if not rows:
        return []
    names = [col[0] for col in cur.description]
    return [dict(zip(names, row)) for row in rows]


def one_row(cur, sql: str, params: tuple = ()) -> dict | None:
    rows = all_rows(cur, sql, params)
    return rows[0] if rows else None

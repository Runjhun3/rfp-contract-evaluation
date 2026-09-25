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

"""Apply numbered SQL files in backend/migrations/ that have not run yet.

Plain SQL on purpose: the committee's DBA can read exactly what runs.
One transaction per file; a failed file leaves the database unchanged.
"""
from pathlib import Path

from app.config import Settings
from app.db.connection import transaction

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"

CREATE_LOG = """create table if not exists schema_migration (
  name text primary key, applied_at timestamptz not null default now())"""


def pending(applied: set[str]) -> list[Path]:
    return [p for p in sorted(MIGRATIONS.glob("*.sql")) if p.name not in applied]


def migrate(settings: Settings) -> list[str]:
    with transaction(settings) as cur:
        cur.execute(CREATE_LOG)
        cur.execute("select name from schema_migration")
        applied = {row[0] for row in cur.fetchall()}
    done = []
    for path in pending(applied):
        with transaction(settings) as cur:
            cur.execute(path.read_text(encoding="utf-8"))
            cur.execute("insert into schema_migration (name) values (%s)", (path.name,))
        done.append(path.name)
    return done

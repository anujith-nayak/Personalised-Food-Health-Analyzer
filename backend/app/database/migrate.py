"""
Database Schema Migration Utility
===================================
Automatically detects missing columns in all SQLAlchemy-managed tables and
adds them using ALTER TABLE — without touching existing data.

Strategy
--------
- Works with both SQLite (dev) and PostgreSQL (prod).
- Reads the actual DB schema via PRAGMA (SQLite) or information_schema (PostgreSQL).
- Compares against the SQLAlchemy model definitions.
- Issues one ALTER TABLE … ADD COLUMN statement per missing column.
- Idempotent: safe to run on every startup.

Usage
-----
Called automatically in app/main.py before the first request.
Can also be run directly:  python -m app.database.migrate
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── SQLAlchemy type → SQL DDL string ──────────────────────────────────────────
# Maps Python SQLAlchemy type names to the correct DDL fragment for each DB.
_SQLITE_TYPE_MAP: dict[str, str] = {
    "BOOLEAN":  "BOOLEAN",
    "INTEGER":  "INTEGER",
    "VARCHAR":  "VARCHAR",
    "STRING":   "VARCHAR",
    "TEXT":     "TEXT",
    "FLOAT":    "FLOAT",
    "NUMERIC":  "NUMERIC",
    "DATETIME": "DATETIME",
    "JSON":     "JSON",
}

_POSTGRES_TYPE_MAP: dict[str, str] = {
    "BOOLEAN":  "BOOLEAN",
    "INTEGER":  "INTEGER",
    "VARCHAR":  "VARCHAR",
    "STRING":   "VARCHAR",
    "TEXT":     "TEXT",
    "FLOAT":    "DOUBLE PRECISION",
    "NUMERIC":  "NUMERIC",
    "DATETIME": "TIMESTAMP",
    "JSON":     "JSONB",
}


def _is_sqlite(engine: Engine) -> bool:
    return engine.dialect.name == "sqlite"


def _existing_columns(engine: Engine, table_name: str) -> set[str]:
    """Return the set of column names that currently exist in the table."""
    insp = inspect(engine)
    try:
        cols = insp.get_columns(table_name)
        return {c["name"].lower() for c in cols}
    except Exception:
        return set()


def _sql_type(col_type: Any, is_sqlite: bool) -> str:
    """Convert a SQLAlchemy column type to a DDL type string."""
    type_name = type(col_type).__name__.upper()
    type_map = _SQLITE_TYPE_MAP if is_sqlite else _POSTGRES_TYPE_MAP
    return type_map.get(type_name, "VARCHAR")


def _default_clause(col, is_sqlite: bool) -> str:
    """Build the DEFAULT … clause for a column, if it has a server default."""
    if col.default is not None and hasattr(col.default, "arg"):
        arg = col.default.arg
        if isinstance(arg, bool):
            return f" DEFAULT {1 if arg else 0}"
        if isinstance(arg, (int, float)):
            return f" DEFAULT {arg}"
        if isinstance(arg, str):
            return f" DEFAULT '{arg}'"
    # All new nullable columns default to NULL — no clause needed
    return ""


def run_migrations(engine: Engine) -> None:
    """
    Inspect every SQLAlchemy-mapped table and add any columns that exist in the
    model but are absent from the actual database table.

    Safe to call on every application startup.
    """
    from app.database.db import Base   # Import here to avoid circular imports

    sqlite = _is_sqlite(engine)
    dialect = "SQLite" if sqlite else "PostgreSQL"
    logger.info(f"[Migration] Running schema check on {dialect}")

    with engine.connect() as conn:
        for mapper in Base.registry.mappers:
            table = mapper.local_table
            table_name = table.name

            existing = _existing_columns(engine, table_name)
            if not existing:
                # Table doesn't exist yet — create_all handles it
                continue

            for col in table.columns:
                col_name = col.name.lower()
                if col_name in existing:
                    continue   # Column already present — skip

                sql_type    = _sql_type(col.type, sqlite)
                default_sql = _default_clause(col, sqlite)
                nullable    = "" if col.nullable else " NOT NULL"

                # SQLite requires nullable or a default for ALTER TABLE ADD COLUMN
                # Since all new columns in our models are nullable, this is fine.
                ddl = (
                    f'ALTER TABLE "{table_name}" '
                    f'ADD COLUMN "{col_name}" {sql_type}{default_sql}'
                )

                try:
                    conn.execute(text(ddl))
                    if sqlite:
                        conn.execute(text("PRAGMA wal_checkpoint"))
                    logger.info(
                        f"[Migration] ✓ Added column: {table_name}.{col_name} "
                        f"({sql_type}{default_sql})"
                    )
                except Exception as exc:
                    # Column may have been added by a concurrent process — log and continue
                    logger.warning(
                        f"[Migration] Could not add {table_name}.{col_name}: {exc}"
                    )

        conn.commit()

    logger.info("[Migration] Schema check complete.")


# ── Standalone runner ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO,
                         format="%(asctime)s [%(levelname)s] %(message)s")

    # Import models so SQLAlchemy registers them with Base
    from app.database.db import engine as _engine
    from app.models import user as _user_models  # noqa: F401

    run_migrations(_engine)
    print("\nMigration complete. Current schema:")

    import sqlite3 as _sqlite3
    _db = _sqlite3.connect("health_app.db")
    _cur = _db.cursor()
    _cur.execute("PRAGMA table_info(health_profiles)")
    for row in _cur.fetchall():
        print(f"  {row[1]:30} {row[2]}")
    _db.close()

"""PostgreSQL connection helpers."""

from __future__ import annotations

import psycopg

# Arbitrary constant shared by every task that runs DDL on the warehouse.
_DDL_LOCK_KEY = 7_413_920_221


def connect(dsn: str) -> psycopg.Connection:
    """Open an autocommit connection.

    Writes are grouped explicitly with ``conn.transaction()``, so each block is
    a real transaction instead of a savepoint inside an implicit one.
    """
    return psycopg.connect(dsn, autocommit=True, application_name="public-spend-pipeline")


def lock_ddl(conn: psycopg.Connection) -> None:
    """Serialize schema changes until the current transaction ends.

    ``CREATE ... IF NOT EXISTS`` is not safe under concurrency: two parallel
    tasks creating the same object can fail with a unique violation.
    """
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (_DDL_LOCK_KEY,))

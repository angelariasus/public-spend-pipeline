"""PostgreSQL connection helper."""

from __future__ import annotations

import psycopg


def connect(dsn: str) -> psycopg.Connection:
    """Open an autocommit connection.

    Writes are grouped explicitly with ``conn.transaction()``, so each block is
    a real transaction instead of a savepoint inside an implicit one.
    """
    return psycopg.connect(dsn, autocommit=True, application_name="public-spend-pipeline")

"""Full-snapshot loads of MEF investment CSVs into ``raw.mef_<dataset>``.

Unlike the OECE bundles, each dataset is one stable table, so it lands with
typed (``text``) columns. Tables are never dropped, so dbt views built on top
of them keep working: new source columns are added, and removed ones stay NULL.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from public_spend.db import lock_ddl

LOAD_LOG_TABLE = "mef_load_log"
_CHUNK_SIZE = 1024 * 1024


def ensure_log_table(conn: psycopg.Connection, schema: str) -> None:
    with conn.transaction():
        lock_ddl(conn)
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {} (
                    dataset        text        NOT NULL,
                    content_sha256 text        NOT NULL,
                    etag           text,
                    last_modified  text,
                    row_count      bigint      NOT NULL,
                    columns        jsonb       NOT NULL,
                    loaded_at      timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY (dataset, loaded_at)
                )
                """
            ).format(sql.Identifier(schema, LOAD_LOG_TABLE))
        )


def ensure_table(
    conn: psycopg.Connection, schema: str, table: str, columns: list[str]
) -> list[str]:
    """Create ``table`` if needed and add any new source columns.

    Returns the columns that had to be added to an existing table.
    """
    target = sql.Identifier(schema, table)
    with conn.transaction():
        lock_ddl(conn)
        existing = _table_columns(conn, schema, table)
        if not existing:
            definitions = [sql.SQL("{} text").format(sql.Identifier(c)) for c in columns]
            definitions.append(sql.SQL("_loaded_at timestamptz NOT NULL DEFAULT now()"))
            conn.execute(
                sql.SQL("CREATE TABLE {} ({})").format(target, sql.SQL(", ").join(definitions))
            )
            return []

        added = [c for c in columns if c not in existing]
        for column in added:
            conn.execute(
                sql.SQL("ALTER TABLE {} ADD COLUMN {} text").format(target, sql.Identifier(column))
            )
        return added


def last_load(conn: psycopg.Connection, schema: str, dataset: str) -> dict | None:
    """Return the validators and hash of the latest load of ``dataset``, if any."""
    row = conn.execute(
        sql.SQL(
            """
            SELECT content_sha256, etag, last_modified
            FROM {}
            WHERE dataset = %s
            ORDER BY loaded_at DESC
            LIMIT 1
            """
        ).format(sql.Identifier(schema, LOAD_LOG_TABLE)),
        (dataset,),
    ).fetchone()
    if row is None:
        return None
    return {"sha256": row[0], "etag": row[1], "last_modified": row[2]}


def load_snapshot(
    conn: psycopg.Connection,
    schema: str,
    dataset: str,
    table: str,
    path: Path,
    columns: list[str],
    content_sha256: str,
    etag: str | None = None,
    last_modified: str | None = None,
) -> int:
    """Replace the contents of ``table`` with the CSV at ``path`` in one transaction."""
    target = sql.Identifier(schema, table)
    statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        target, sql.SQL(", ").join(sql.Identifier(c) for c in columns)
    )
    with conn.transaction():
        conn.execute(sql.SQL("TRUNCATE {}").format(target))
        with conn.cursor() as cur:
            with cur.copy(statement) as copy, path.open("rb") as fh:
                while chunk := fh.read(_CHUNK_SIZE):
                    copy.write(chunk)
            row_count = cur.rowcount
        conn.execute(
            sql.SQL(
                """
                INSERT INTO {} (dataset, content_sha256, etag, last_modified, row_count, columns)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(schema, LOAD_LOG_TABLE)),
            (dataset, content_sha256, etag, last_modified, row_count, Jsonb(columns)),
        )
    return row_count


def record_unchanged(
    conn: psycopg.Connection,
    schema: str,
    dataset: str,
    etag: str | None,
    last_modified: str | None,
) -> None:
    """Refresh the stored validators when the content hash shows no change."""
    log_table = sql.Identifier(schema, LOAD_LOG_TABLE)
    conn.execute(
        sql.SQL(
            """
            UPDATE {} SET etag = %s, last_modified = %s
            WHERE dataset = %s
              AND loaded_at = (SELECT max(loaded_at) FROM {} WHERE dataset = %s)
            """
        ).format(log_table, log_table),
        (etag, last_modified, dataset, dataset),
    )


def _table_columns(conn: psycopg.Connection, schema: str, table: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """,
        (schema, table),
    ).fetchall()
    return {row[0] for row in rows}

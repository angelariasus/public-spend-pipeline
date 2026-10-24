"""Idempotent loading of OCDS tables into the ``raw`` schema.

Each OCDS table lands in ``raw.oece_<table>`` with one JSONB document per CSV
row. Columns vary between months, so storing rows as documents avoids schema
migrations at load time; dbt staging models pick the fields they need.

A period is always replaced as a whole inside one transaction, so re-running
a load never duplicates rows and a failed load leaves the previous data intact.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from public_spend.config import Period
from public_spend.oece.archive import iter_rows

LOAD_LOG_TABLE = "oece_load_log"


def raw_table(table: str) -> str:
    return f"oece_{table}"


def ensure_raw_tables(conn: psycopg.Connection, schema: str, tables: Iterable[str]) -> None:
    """Create the raw schema, the load log and one table per OCDS table."""
    with conn.transaction():
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {} (
                    source              text        NOT NULL,
                    period              date        NOT NULL,
                    content_sha256      text        NOT NULL,
                    source_published_at timestamptz,
                    row_counts          jsonb       NOT NULL,
                    loaded_at           timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY (source, period)
                )
                """
            ).format(sql.Identifier(schema, LOAD_LOG_TABLE))
        )
        for table in tables:
            conn.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        source       text        NOT NULL,
                        period       date        NOT NULL,
                        row_number   integer     NOT NULL,
                        data         jsonb       NOT NULL,
                        _source_file text        NOT NULL,
                        _loaded_at   timestamptz NOT NULL DEFAULT now(),
                        PRIMARY KEY (source, period, row_number)
                    )
                    """
                ).format(sql.Identifier(schema, raw_table(table)))
            )


def loaded_sha256(conn: psycopg.Connection, schema: str, source: str, period: Period) -> str | None:
    """Return the content hash of the last successful load of a period, if any."""
    row = conn.execute(
        sql.SQL("SELECT content_sha256 FROM {} WHERE source = %s AND period = %s").format(
            sql.Identifier(schema, LOAD_LOG_TABLE)
        ),
        (source, period.first_day),
    ).fetchone()
    return row[0] if row else None


def load_period(
    conn: psycopg.Connection,
    schema: str,
    source: str,
    period: Period,
    zip_path: Path,
    members: dict[str, str],
    tables: Iterable[str],
    content_sha256: str,
    published_at: str | None = None,
) -> dict[str, int]:
    """Replace every configured table's rows for ``(source, period)``.

    ``tables`` is the full configured list: tables missing from this bundle
    are still cleared, so stale rows from an earlier load cannot survive.
    Returns the number of rows loaded per table.
    """
    counts: dict[str, int] = {}
    with conn.transaction():
        for table in tables:
            target = sql.Identifier(schema, raw_table(table))
            conn.execute(
                sql.SQL("DELETE FROM {} WHERE source = %s AND period = %s").format(target),
                (source, period.first_day),
            )
            member = members.get(table)
            if member is None:
                counts[table] = 0
                continue
            counts[table] = _copy_rows(conn, target, source, period, zip_path, member)

        conn.execute(
            sql.SQL(
                """
                INSERT INTO {} (source, period, content_sha256, source_published_at, row_counts)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source, period) DO UPDATE SET
                    content_sha256      = EXCLUDED.content_sha256,
                    source_published_at = EXCLUDED.source_published_at,
                    row_counts          = EXCLUDED.row_counts,
                    loaded_at           = now()
                """
            ).format(sql.Identifier(schema, LOAD_LOG_TABLE)),
            (source, period.first_day, content_sha256, published_at, Jsonb(counts)),
        )
    return counts


def _copy_rows(
    conn: psycopg.Connection,
    target: sql.Identifier,
    source: str,
    period: Period,
    zip_path: Path,
    member: str,
) -> int:
    count = 0
    statement = sql.SQL(
        "COPY {} (source, period, row_number, data, _source_file) FROM STDIN"
    ).format(target)
    with conn.cursor() as cur, cur.copy(statement) as copy:
        for count, row in enumerate(iter_rows(zip_path, member), start=1):
            copy.write_row(
                (source, period.first_day, count, json.dumps(row, ensure_ascii=False), member)
            )
    return count

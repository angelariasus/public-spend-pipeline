"""Entry points used by the Airflow DAG (also runnable from the command line)."""

from __future__ import annotations

import argparse
import logging
import tempfile
from pathlib import Path

import requests

from public_spend.config import Period, Settings
from public_spend.db import connect
from public_spend.http import build_session
from public_spend.oece import archive, index, load

log = logging.getLogger(__name__)


def plan(settings: Settings, session: requests.Session | None = None) -> list[index.FileEntry]:
    """Create the raw tables if needed and list the monthly files in scope."""
    session = session or build_session(settings.user_agent)
    entries = index.fetch_index(session, settings.oece_base_url, settings.http_timeout_seconds)
    selected = index.select_entries(
        entries, settings.oece_source, settings.oece_start_period, settings.oece_end_period
    )
    with connect(settings.warehouse_dsn) as conn:
        load.ensure_raw_tables(conn, settings.raw_schema, settings.oece_tables)
    log.info("Planned %d period(s) out of %d index entries", len(selected), len(entries))
    return selected


def ingest(
    settings: Settings,
    entry: index.FileEntry,
    session: requests.Session | None = None,
) -> dict:
    """Download one monthly bundle and load it, unless its content is unchanged."""
    session = session or build_session(settings.user_agent)
    with tempfile.TemporaryDirectory(prefix="oece-") as tmp:
        zip_path = archive.download(
            session,
            entry.csv_url,
            Path(tmp) / f"{entry.source}_{entry.period}.zip",
            settings.http_timeout_seconds,
        )
        members = archive.find_members(zip_path, settings.oece_tables)
        digest = archive.content_sha256(zip_path, members)

        with connect(settings.warehouse_dsn) as conn:
            previous = load.loaded_sha256(conn, settings.raw_schema, entry.source, entry.period)
            if previous == digest:
                log.info("%s %s unchanged, skipping", entry.source, entry.period)
                return {"period": str(entry.period), "status": "unchanged"}

            counts = load.load_period(
                conn,
                settings.raw_schema,
                entry.source,
                entry.period,
                zip_path,
                members,
                settings.oece_tables,
                digest,
                entry.published_at,
            )

    missing = sorted(set(settings.oece_tables) - set(members))
    if missing:
        log.warning("%s %s: tables missing from bundle: %s", entry.source, entry.period, missing)
    log.info("%s %s loaded: %s", entry.source, entry.period, counts)
    return {"period": str(entry.period), "status": "loaded", "rows": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load OECE OCDS bulk files into Postgres.")
    parser.add_argument("--period", help="Load a single YYYY-MM period instead of the full range")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    session = build_session(settings.user_agent)
    entries = plan(settings, session)
    if args.period:
        wanted = Period.parse(args.period)
        entries = [entry for entry in entries if entry.period == wanted]
        if not entries:
            raise SystemExit(f"period {wanted} is not in the index or outside the configured range")
    for entry in entries:
        ingest(settings, entry, session)


if __name__ == "__main__":
    main()

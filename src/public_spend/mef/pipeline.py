"""Entry point used by the Airflow DAG (also runnable from the command line)."""

from __future__ import annotations

import argparse
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from public_spend.config import Settings
from public_spend.db import connect
from public_spend.http import build_session
from public_spend.mef import load, source

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dataset:
    name: str
    table: str
    url: str


def datasets(settings: Settings) -> dict[str, Dataset]:
    """MEF publishes active and closed investments as two disjoint files."""
    return {
        "investments": Dataset("investments", "mef_investments", settings.mef_investments_url),
        "closed_investments": Dataset(
            "closed_investments", "mef_closed_investments", settings.mef_closed_investments_url
        ),
    }


def ingest(settings: Settings, name: str, session: requests.Session | None = None) -> dict:
    """Load one dataset unless the server or the content hash says it is unchanged."""
    dataset = datasets(settings)[name]
    session = session or build_session(settings.user_agent)
    schema = settings.raw_schema

    with connect(settings.warehouse_dsn) as conn:
        load.ensure_log_table(conn, schema)
        previous = load.last_load(conn, schema, dataset.name) or {}

        with tempfile.TemporaryDirectory(prefix="mef-") as tmp:
            result = source.download(
                session,
                dataset.url,
                Path(tmp) / f"{dataset.name}.csv",
                etag=previous.get("etag"),
                last_modified=previous.get("last_modified"),
                timeout=settings.http_timeout_seconds,
            )
            if result is None:
                log.info("MEF %s not modified on the server, skipping", dataset.name)
                return {"dataset": dataset.name, "status": "not_modified"}

            if previous.get("sha256") == result.sha256:
                load.record_unchanged(conn, schema, dataset.name, result.etag, result.last_modified)
                log.info("MEF %s content unchanged, skipping", dataset.name)
                return {"dataset": dataset.name, "status": "unchanged"}

            columns = source.read_columns(result.path)
            added = load.ensure_table(conn, schema, dataset.table, columns)
            if added:
                log.warning("New MEF %s columns added to raw table: %s", dataset.name, added)
            rows = load.load_snapshot(
                conn,
                schema,
                dataset.name,
                dataset.table,
                result.path,
                columns,
                result.sha256,
                result.etag,
                result.last_modified,
            )

    log.info("MEF %s loaded: %d rows, %d columns", dataset.name, rows, len(columns))
    return {
        "dataset": dataset.name,
        "status": "loaded",
        "rows": rows,
        "columns": len(columns),
        "added_columns": added,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load MEF investment CSVs into Postgres.")
    parser.add_argument("--dataset", choices=["investments", "closed_investments"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    names = [args.dataset] if args.dataset else list(datasets(settings))
    for name in names:
        print(ingest(settings, name))


if __name__ == "__main__":
    main()

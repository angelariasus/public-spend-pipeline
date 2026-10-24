"""Daily ingestion of OECE procurement data (OCDS bulk CSV files) into ``raw``.

One mapped task per month: each downloads the bundle, skips it when the CSV
content is unchanged since the last load, and otherwise replaces that month's
rows in a single transaction.
"""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="oece_ingest",
    # OECE refreshes its bulk files daily from 08:15 Lima time.
    schedule="30 9 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Lima"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ingestion", "oece"],
)
def oece_ingest():
    @task
    def plan_periods() -> list[dict[str, str]]:
        from public_spend.config import Settings
        from public_spend.oece.pipeline import plan

        return [entry.to_dict() for entry in plan(Settings.from_env())]

    # Two concurrent downloads keep the load on the public portal modest.
    @task(max_active_tis_per_dag=2)
    def load_period(entry: dict[str, str]) -> dict:
        from public_spend.config import Settings
        from public_spend.oece.index import FileEntry
        from public_spend.oece.pipeline import ingest

        return ingest(Settings.from_env(), FileEntry.from_dict(entry))

    load_period.expand(entry=plan_periods())


oece_ingest()

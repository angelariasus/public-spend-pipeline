"""Daily ingestion of MEF public investment data into ``raw``.

MEF publishes active and closed investments as two full-snapshot CSVs
(~250 MB and ~120 MB). Each one is a mapped task: a conditional request skips
the download when the server reports no change; otherwise its table is
replaced atomically.
"""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="mef_ingest",
    schedule="0 10 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Lima"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["ingestion", "mef"],
)
def mef_ingest():
    @task
    def load_dataset(name: str) -> dict:
        from public_spend.config import Settings
        from public_spend.mef.pipeline import ingest

        return ingest(Settings.from_env(), name)

    load_dataset.expand(name=["investments", "closed_investments"])


mef_ingest()

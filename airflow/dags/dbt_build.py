"""Builds the dbt project (staging, intermediate and marts) after ingestion.

Asset-aware schedule: a run starts once both raw layers have been loaded since
the previous run, so the warehouse is rebuilt once a day after the OECE and
MEF DAGs finish. Source freshness is checked first; a stale source stops the
build.

dbt lives in its own virtualenv in the image. The project is mounted
read-only and copied to a temporary directory, so runs never write target/ or
dbt_packages/ into the repository.
"""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.sdk import Asset, dag, task

RAW_OECE = Asset("raw_oece")
RAW_MEF = Asset("raw_mef")
MARTS = Asset("marts")

DBT_COMMAND = """
set -euo pipefail
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
tar -C /opt/airflow/dbt --exclude=./target --exclude=./logs --exclude=./dbt_packages -cf - . \\
    | tar -C "$workdir" -xf -
cd "$workdir"
export DBT_PROFILES_DIR="$workdir" DBT_USE_COLORS=false
/opt/dbt-venv/bin/dbt deps --quiet
/opt/dbt-venv/bin/dbt {args}
"""


@dag(
    dag_id="dbt_build",
    schedule=(RAW_OECE & RAW_MEF),
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Lima"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["transformation", "dbt"],
)
def dbt_build():
    @task.bash
    def source_freshness() -> str:
        return DBT_COMMAND.format(args="source freshness")

    @task.bash(outlets=[MARTS])
    def build() -> str:
        return DBT_COMMAND.format(args="build")

    source_freshness() >> build()


dbt_build()

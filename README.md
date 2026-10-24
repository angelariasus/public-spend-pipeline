# public-spend-pipeline

An end-to-end ELT pipeline that links Peru's public procurement contracts
(OECE / SEACE, published in the Open Contracting Data Standard) with public
investment execution data from the Ministry of Economy and Finance (MEF), to
measure how much is contracted versus how much is actually delivered.

> Status: work in progress. Ingestion of OECE procurement data is done;
> MEF ingestion, dbt models and dashboards are next.

## Questions this project answers

1. Which public entities award the most money, and in which categories?
2. How concentrated are awards among suppliers, per entity?
3. For each public investment project: how much was contracted versus what
   MEF reports as spent and physically completed?
4. Which projects have large contracted amounts but little progress?
5. How does all of the above vary by region, level of government and month?

## Architecture

```
OECE OCDS API ──┐                                        ┌─> Metabase (planned)
                ├─> Airflow ─> Postgres `raw` ─> dbt ────┤
MEF CSV ────────┘   (Python)   (as landed)    (planned)  └─> Power BI (later)
```

| Layer          | Tool                                         |
|----------------|----------------------------------------------|
| Orchestration  | Apache Airflow 3.3 (LocalExecutor)           |
| Ingestion      | Python (`requests`, `psycopg`)               |
| Warehouse      | PostgreSQL 16                                |
| Transformation | dbt-core (planned)                           |
| BI             | Metabase (planned), Power BI (later)         |
| Tooling        | uv, ruff, pytest, pre-commit, GitHub Actions |

## Data sources

| Source | Access | Notes |
|--------|--------|-------|
| [OECE Open Contracting portal](https://contratacionesabiertas.oece.gob.pe/descargas) | `GET /api/v1/files` (paginated index) and `GET /api/v1/file/seace_v3/csv/{year}/{month}/` (ZIP with one CSV per OCDS table) | CC BY 4.0. Refreshed daily. |
| [MEF public investment detail](https://www.datosabiertos.gob.pe/dataset/informaci%C3%B3n-de-inversiones-p%C3%BAblicas-2001%E2%80%932026-mef) | Single CSV (~250 MB) | Planned. |

The two sources join on the investment project code: OCDS
`planning/budget/projectID` equals MEF `CODIGO_UNICO` (98% match rate on a
sample month).

## OECE ingestion

The `oece_ingest` DAG runs daily at 09:30 Lima time, after the portal
refreshes its files.

1. `plan_periods` reads the whole file index, keeps `seace_v3` months between
   `OECE_START_PERIOD` and `OECE_END_PERIOD`, and creates the raw tables.
2. `load_period` runs once per month (dynamic task mapping, two at a time to
   be gentle with the portal). It downloads the ZIP, hashes the content of the
   selected CSVs and compares it with the last load:
   - unchanged content: the month is skipped;
   - new or changed content: the month is replaced in a single transaction.

Design decisions:

- **Rows land as JSONB documents** in `raw.oece_<table>`, one per CSV row.
  OCDS columns vary from month to month, so this avoids schema migrations at
  load time; dbt staging models select and type the fields they need.
- **Change detection uses a content hash.** The portal regenerates every
  monthly file daily, so neither the index timestamp nor the ZIP checksum it
  publishes says whether the data changed.
- **Loads are idempotent and atomic.** A month is deleted and reinserted in one
  transaction; re-running never duplicates rows and a failed load keeps the
  previous data. Every load is recorded in `raw.oece_load_log`.
- **A browser User-Agent is sent** because the portals answer HTTP 418 to
  generic clients.

Tables loaded by default (configurable with `OECE_TABLES`): `records`,
`com_parties`, `com_ten_items`, `com_ten_ite_additionalclassific`,
`com_ten_tenderers`, `com_awards`, `com_awa_suppliers`, `com_contracts`.

## Getting started

Requirements: Docker with ~6 GB of memory, and [uv](https://docs.astral.sh/uv/)
for local development.

```bash
cp .env.example .env        # then replace every change-me value
docker compose up -d --build
```

- Airflow UI: <http://localhost:8080> (user and password from `.env`)
- Warehouse: `postgresql://<WAREHOUSE_USER>:<WAREHOUSE_PASSWORD>@localhost:5433/warehouse`

Enable the `oece_ingest` DAG in the UI, or load a single month from the command
line:

```bash
docker compose exec airflow-scheduler python -m public_spend.oece.pipeline --period 2024-01
```

## Development

```bash
uv sync
uv run pre-commit install
uv run ruff check . && uv run ruff format --check .
uv run pytest                 # integration tests are skipped without a database
```

Integration tests need a PostgreSQL database; each test uses a throwaway
schema:

```bash
TEST_DATABASE_URL=postgresql://warehouse:<password>@localhost:5433/warehouse uv run pytest
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/),
enforced by a `commit-msg` hook.

## Project structure

```
├── airflow/dags/          # Airflow DAGs (thin wrappers around src/)
├── docker/                # Airflow image and Postgres init script
├── src/public_spend/      # Ingestion package
│   └── oece/              # index client, bundle reader, raw loader, entry points
├── tests/                 # unit and integration tests
└── docker-compose.yml
```

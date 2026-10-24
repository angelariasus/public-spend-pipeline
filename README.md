# public-spend-pipeline

An end-to-end ELT pipeline that links Peru's public procurement contracts
(OECE / SEACE, published in the Open Contracting Data Standard) with public
investment execution data from the Ministry of Economy and Finance (MEF), to
measure how much is contracted versus how much is actually delivered.

> Status: work in progress.

## Stack

| Layer          | Tool                                  |
|----------------|---------------------------------------|
| Orchestration  | Apache Airflow 3 (LocalExecutor)      |
| Ingestion      | Python (`requests`, `psycopg`)        |
| Warehouse      | PostgreSQL 16                         |
| Transformation | dbt-core (planned)                    |
| BI             | Metabase (planned), Power BI (later)  |
| Tooling        | uv, ruff, pytest, pre-commit, GitHub Actions |

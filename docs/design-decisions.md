# Design decisions and known limitations

Short records of the choices that shaped the pipeline, with the reasons and
the alternatives that were rejected. Numbers refer to the 2024-01 to 2026-10
scope.

## Ingestion

### 1. Land OCDS rows as JSONB, not typed columns

OECE regenerates its monthly files daily and the set of CSV columns changes
over time (new fields appear, a few disappear). Creating typed raw tables from
each header would mean schema migrations at load time and a loader that knows
every field. Instead each CSV row lands as one JSONB document in
`raw.oece_<table>`, keyed by `(source, period, row_number)`; dbt staging
models select and cast only the fields they use. The cost is paid once by
materializing staging as indexed tables.

### 2. Detect changes by hashing content, not metadata

The portal's index timestamps change every day for every month, and the SHA it
publishes does not match the CSV ZIP. The loader hashes the bytes of the
selected CSV members and compares them with the last load of that month; only
changed months are reloaded. Unchanged months cost one download and no
writes.

### 3. Replace a month atomically; never drop a table

A month is deleted and reinserted inside one transaction, so a failed load
leaves the previous data and a re-run never duplicates rows. MEF snapshots use
`TRUNCATE` + `COPY` in one transaction for the same reason. Tables are never
dropped and new MEF columns are added with `ALTER TABLE`, because dbt objects
depend on them.

### 4. Serialize DDL with an advisory lock

Mapped tasks run in parallel and `CREATE TABLE IF NOT EXISTS` on the same
object can still fail under concurrency in Postgres. All DDL runs under
`pg_advisory_xact_lock`, which an integration test exercises with concurrent
connections.

### 5. Two MEF files, not one

The active-investments file alone matched 77% of the 2024 project codes.
Finished projects move to the closed-investments file, which raised coverage
to 95%. Both are loaded and unioned in `intermediate`.

## Transformation

### 6. Defensive casts

Source values are text and occasionally malformed. The `to_numeric`,
`to_timestamptz`, `to_local_timestamp`, `yyyymm_to_date` and `to_yes_no`
macros validate the format with a regular expression and return NULL
otherwise, so one bad value never fails a build; tests on the staging models
catch unexpected NULL rates.

### 7. Composite keys in staging, surrogate keys in facts

OCDS `award_id` and `contract_id` repeat across processes, so staging keys are
`(ocid, award_id)` and `(ocid, contract_id)`, tested with
`unique_combination_of_columns` and a custom `composite_relationships` test.
Facts add `award_key` and `contract_key` (MD5 surrogates) because BI tools
relate tables on single columns.

### 8. Convert to soles with a fallback chain

About 2% of awards and contracts are in USD, EUR or other currencies. Most
awards report their own rate; half of the foreign-currency contracts do not.
The chain is: rate reported by the record, then the rate reported by the
contract's award, then the average rate of that currency in that month (from
all reported rates), then the currency's average over all months.
`exchange_rate_source` records which step applied. Alternative rejected:
official central bank (BCRP) rates would need another source and a date-level
join; the reported rates are what the entities themselves used.

### 9. Split multi-project processes equally

1.2% of the processes linked to an investment fund several projects, and
OCDS does not say how their amount is distributed. The bridge assigns each
project `1 / project_count` of the process amount. A singular test checks that
the split neither loses nor duplicates money. Alternative rejected: weighting
by each project's cost would attribute amounts the entity never declared.

### 10. Thresholds for the flags

- `is_lagging`: active project, at least S/ 1M contracted, first contract
  signed more than 12 months ago, physical progress below 25%. The amount
  excludes small purchases; the 12 months give works time to start.
- `is_contracted_above_cost`: contracted amount above 150% of the updated
  cost. Below that, cost updates and additional works explain most gaps.

Both are columns, not filters, so a dashboard can change the question
without changing the model.

### 11. Staging as tables, intermediate as views, marts as tables

Staging extracts from multi-million-row JSONB tables, so it is materialized
once per run with indexes. Intermediate models are light joins over those
tables and are only read by the marts, so views avoid a copy. Marts are what
BI tools query and are tables with indexes on their keys.

## Orchestration and BI

### 12. dbt inside the Airflow image, in its own virtualenv

dbt and Airflow pin overlapping libraries; installing both in one environment
either fails to resolve or breaks on upgrade. The image keeps dbt in
`/opt/dbt-venv`. The project directory is mounted read-only and copied to a
temporary directory per run, so `target/` and `dbt_packages/` never land in
the repository.

### 13. Asset-aware scheduling instead of a fixed time

`dbt_build` runs when both `raw_oece` and `raw_mef` have been updated since
its previous run, so a slow or failed ingestion delays the build instead of
building on stale data. Source freshness is checked first.

### 14. A read-only role for BI, granted by dbt

Metabase (and later Power BI) connect as `bi_reader`, which can only read the
`marts` schema. dbt grants `SELECT` on each mart it builds and `USAGE` on the
schema in an `on-run-end` hook, so a rebuild cannot silently drop the grants.

### 15. Dashboards as code

Questions are SQL files linted in CI; the layout is Python. A provisioning
service upserts them through the Metabase API by name, which makes the
dashboards reproducible from a clean install and reviewable in pull requests.

### 16. No notebooks

All analysis lives in tested `.py` and `.sql` files, so every number in the
documentation can be regenerated by a scheduled run.

## Known limitations

- **Scope starts in January 2024.** Accrued spend and cost in MEF cover the
  whole life of a project, so `accrued_to_contracted_pct` is above 100% for
  projects contracted before 2024. The lagging flag only sees contracts in
  scope.
- **Two meanings of "department".** In procurement marts it is the address of
  the buying entity (48% of the awarded amount sits in Lima, where national
  entities are based); in investment marts it is where the project is
  located.
- **Source tagging errors.** Entities sometimes tag processes with the wrong
  project code; the largest case charges S/ 1.6 billion of works to a sports
  court costing S/ 0.8 million. `is_contracted_above_cost` surfaces these
  rather than hiding them.
- **Awards without a supplier and contracts without an award.** ~3k awards
  are published without a supplier and ~1k contracts reference an award
  missing from their process. They stay in the facts with NULL keys.
- **Physical progress only for active projects.** The closed file has no
  progress column; closed projects are excluded from the lagging flag.
- **Concentration on small entities.** An entity with two awards in a year is
  trivially concentrated. The dashboard table filters entities with at least
  S/ 10M awarded in the year; the mart keeps every entity.
- **Latest values only.** Dimensions hold the most recent name and address;
  the pipeline keeps no history of changes (no slowly changing dimensions),
  and reloaded months overwrite the previous version.
- **Exchange rates are averages of reported rates**, not official daily
  rates. They apply to 92 awards and 69 contracts; the rest use their own
  rate.
- **Code pages.** MEF files contain a few mis-encoded characters in names;
  they are kept as published.

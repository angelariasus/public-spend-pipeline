import pytest
import responses

from public_spend.config import Period, Settings
from public_spend.http import build_session
from public_spend.oece import load
from public_spend.oece.archive import find_members
from public_spend.oece.index import FileEntry
from public_spend.oece.pipeline import ingest

pytestmark = pytest.mark.integration

TABLES = ("records", "com_awards")
SOURCE = "seace_v3"
RECORDS = "ocid,compiledRelease/buyer/name\nocds-1,ENTIDAD A\nocds-2,ENTIDAD B\n"
AWARDS = "ocid,compiledRelease/awards/0/value/amount\nocds-1,100.5\n"


def _count(conn, schema, table, period=None):
    query = f'SELECT count(*) FROM "{schema}"."oece_{table}"'
    params = ()
    if period:
        query += " WHERE period = %s"
        params = (period.first_day,)
    return conn.execute(query, params).fetchone()[0]


def _load(conn, schema, bundle, period, digest="sha-1"):
    members = find_members(bundle, TABLES)
    return load.load_period(conn, schema, SOURCE, period, bundle, members, TABLES, digest)


def test_load_period_writes_rows_and_log(pg_conn, raw_schema, make_bundle):
    load.ensure_raw_tables(pg_conn, raw_schema, TABLES)
    bundle = make_bundle({"records.csv": RECORDS, "com_awards.csv": AWARDS})

    counts = _load(pg_conn, raw_schema, bundle, Period(2024, 1))

    assert counts == {"records": 2, "com_awards": 1}
    data = pg_conn.execute(
        f'SELECT data FROM "{raw_schema}".oece_com_awards WHERE row_number = 1'
    ).fetchone()[0]
    assert data == {"ocid": "ocds-1", "compiledRelease/awards/0/value/amount": "100.5"}
    assert load.loaded_sha256(pg_conn, raw_schema, SOURCE, Period(2024, 1)) == "sha-1"


def test_reloading_a_period_replaces_it_and_leaves_others(pg_conn, raw_schema, make_bundle):
    load.ensure_raw_tables(pg_conn, raw_schema, TABLES)
    full = make_bundle({"records.csv": RECORDS, "com_awards.csv": AWARDS}, name="full.zip")
    jan, feb = Period(2024, 1), Period(2024, 2)
    _load(pg_conn, raw_schema, full, jan)
    _load(pg_conn, raw_schema, full, feb)

    # February is republished without the awards file and with one record.
    smaller = make_bundle({"records.csv": "ocid\nocds-3\n"}, name="small.zip")
    counts = _load(pg_conn, raw_schema, smaller, feb, digest="sha-2")

    assert counts == {"records": 1, "com_awards": 0}
    assert _count(pg_conn, raw_schema, "records", feb) == 1
    assert _count(pg_conn, raw_schema, "com_awards", feb) == 0
    assert _count(pg_conn, raw_schema, "records", jan) == 2
    assert load.loaded_sha256(pg_conn, raw_schema, SOURCE, feb) == "sha-2"


def test_failed_load_keeps_previous_data(pg_conn, raw_schema, make_bundle):
    load.ensure_raw_tables(pg_conn, raw_schema, TABLES)
    period = Period(2024, 1)
    _load(pg_conn, raw_schema, make_bundle({"records.csv": RECORDS}, name="ok.zip"), period)

    broken = make_bundle({"records.csv": "ocid\nocds-1,extra\n"}, name="broken.zip")
    with pytest.raises(Exception, match="more fields"):
        _load(pg_conn, raw_schema, broken, period, digest="sha-broken")

    assert _count(pg_conn, raw_schema, "records", period) == 2
    assert load.loaded_sha256(pg_conn, raw_schema, SOURCE, period) == "sha-1"


@responses.activate
def test_ingest_skips_unchanged_content(pg_dsn, pg_conn, raw_schema, make_bundle):
    url = "https://example.org/api/v1/file/seace_v3/csv/2024/01/"
    responses.get(url, body=make_bundle({"records.csv": RECORDS}).read_bytes())
    settings = Settings(
        warehouse_dsn=pg_dsn,
        oece_start_period=Period(2024, 1),
        oece_tables=TABLES,
        raw_schema=raw_schema,
    )
    load.ensure_raw_tables(pg_conn, raw_schema, TABLES)
    entry = FileEntry(SOURCE, Period(2024, 1), url, "2026-10-23T14:27:08-05:00")
    session = build_session("ua", retries=0)

    first = ingest(settings, entry, session)
    second = ingest(settings, entry, session)

    assert first == {
        "period": "2024-01",
        "status": "loaded",
        "rows": {"records": 2, "com_awards": 0},
    }
    assert second == {"period": "2024-01", "status": "unchanged"}
    assert _count(pg_conn, raw_schema, "records") == 2

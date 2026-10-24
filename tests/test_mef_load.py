from concurrent.futures import ThreadPoolExecutor

import pytest
import responses

from public_spend.config import Period, Settings
from public_spend.db import connect
from public_spend.http import build_session
from public_spend.mef import load
from public_spend.mef.pipeline import ingest
from public_spend.mef.source import read_columns

pytestmark = pytest.mark.integration

DATASET, TABLE = "investments", "mef_investments"
URL = "https://example.org/DETALLE_INVERSIONES.csv"
CLOSED_URL = "https://example.org/CIERRE_INVERSIONES.csv"
V1 = (
    '﻿"NIVEL","ENTIDAD","CODIGO_UNICO","MONTO_VIABLE"\n'
    '"GL","MUNICIPALIDAD A","2387471","1853953.5"\n'
    '"GR","GOBIERNO REGIONAL B","2522559",\n'
)
V2 = (
    '"NIVEL","ENTIDAD","CODIGO_UNICO","MONTO_VIABLE","ANIO_PROCESO"\n'
    '"GN","MINISTERIO C","2700000","10","2026"\n'
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _load(conn, schema, path, sha):
    columns = read_columns(path)
    load.ensure_log_table(conn, schema)
    added = load.ensure_table(conn, schema, TABLE, columns)
    return added, load.load_snapshot(conn, schema, DATASET, TABLE, path, columns, sha)


def _rows(conn, schema, table=TABLE):
    return conn.execute(
        f'SELECT codigo_unico, monto_viable FROM "{schema}"."{table}" ORDER BY 1'
    ).fetchall()


def test_load_snapshot_creates_table_and_loads_rows(pg_conn, raw_schema, tmp_path):
    added, rows = _load(pg_conn, raw_schema, _write(tmp_path, "v1.csv", V1), "sha-1")

    assert (added, rows) == ([], 2)
    # Unquoted empty fields load as NULL.
    assert _rows(pg_conn, raw_schema) == [("2387471", "1853953.5"), ("2522559", None)]
    assert load.last_load(pg_conn, raw_schema, DATASET) == {
        "sha256": "sha-1",
        "etag": None,
        "last_modified": None,
    }


def test_reload_replaces_rows_and_adds_new_columns(pg_conn, raw_schema, tmp_path):
    _load(pg_conn, raw_schema, _write(tmp_path, "v1.csv", V1), "sha-1")

    added, rows = _load(pg_conn, raw_schema, _write(tmp_path, "v2.csv", V2), "sha-2")

    assert (added, rows) == (["anio_proceso"], 1)
    assert _rows(pg_conn, raw_schema) == [("2700000", "10")]
    assert load.last_load(pg_conn, raw_schema, DATASET)["sha256"] == "sha-2"


def test_failed_load_keeps_previous_snapshot(pg_conn, raw_schema, tmp_path):
    _load(pg_conn, raw_schema, _write(tmp_path, "v1.csv", V1), "sha-1")
    broken = _write(tmp_path, "broken.csv", V1 + '"GL","X","1","2","extra"\n')

    with pytest.raises(Exception, match="extra data"):
        _load(pg_conn, raw_schema, broken, "sha-broken")

    assert len(_rows(pg_conn, raw_schema)) == 2
    assert load.last_load(pg_conn, raw_schema, DATASET)["sha256"] == "sha-1"


def test_concurrent_ddl_does_not_fail(pg_dsn, raw_schema):
    def ensure(_):
        with connect(pg_dsn) as conn:
            load.ensure_log_table(conn, raw_schema)
            load.ensure_table(conn, raw_schema, TABLE, ["codigo_unico"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(ensure, range(8)))


def _settings(pg_dsn, raw_schema):
    return Settings(
        warehouse_dsn=pg_dsn,
        oece_start_period=Period(2024, 1),
        mef_investments_url=URL,
        mef_closed_investments_url=CLOSED_URL,
        raw_schema=raw_schema,
    )


@responses.activate
def test_ingest_skips_when_not_modified_or_unchanged(pg_dsn, raw_schema):
    settings = _settings(pg_dsn, raw_schema)
    session = build_session("ua", retries=0)
    headers = {"ETag": '"v1"', "Last-Modified": "Thu, 22 Oct 2026 18:31:38 GMT"}

    responses.get(URL, body=V1.encode(), headers=headers)
    assert ingest(settings, "investments", session) == {
        "dataset": "investments",
        "status": "loaded",
        "rows": 2,
        "columns": 4,
        "added_columns": [],
    }

    # The server honours the validators sent from the previous load.
    responses.replace(
        responses.GET,
        URL,
        status=304,
        match=[responses.matchers.header_matcher({"If-None-Match": '"v1"'})],
    )
    assert ingest(settings, "investments", session)["status"] == "not_modified"

    # A server that ignores validators is still caught by the content hash.
    responses.replace(responses.GET, URL, body=V1.encode(), headers={"ETag": '"v1b"'})
    assert ingest(settings, "investments", session)["status"] == "unchanged"


@responses.activate
def test_datasets_are_tracked_independently(pg_dsn, pg_conn, raw_schema):
    settings = _settings(pg_dsn, raw_schema)
    session = build_session("ua", retries=0)
    responses.get(URL, body=V1.encode())
    responses.get(CLOSED_URL, body=V2.encode())

    assert ingest(settings, "investments", session)["rows"] == 2
    assert ingest(settings, "closed_investments", session)["rows"] == 1

    assert len(_rows(pg_conn, raw_schema, "mef_investments")) == 2
    assert _rows(pg_conn, raw_schema, "mef_closed_investments") == [("2700000", "10")]
    assert (
        load.last_load(pg_conn, raw_schema, "investments")["sha256"]
        != (load.last_load(pg_conn, raw_schema, "closed_investments")["sha256"])
    )

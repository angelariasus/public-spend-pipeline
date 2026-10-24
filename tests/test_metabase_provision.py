import json

import pytest
import responses

from public_spend.metabase import provision as prov
from public_spend.metabase.client import Metabase, MetabaseError
from public_spend.metabase.content import QUESTIONS

URL = "http://metabase.test"


def settings(tmp_path, **overrides):
    for question in QUESTIONS:
        (tmp_path / f"{question.key}.sql").write_text(f"select 1 as {question.key}")
    env = {
        "METABASE_URL": URL,
        "METABASE_ADMIN_EMAIL": "admin@example.com",
        "METABASE_ADMIN_PASSWORD": "secret-1",
        "WAREHOUSE_DB": "warehouse",
        "BI_READER_USER": "bi_reader",
        "BI_READER_PASSWORD": "reader-secret",
        "METABASE_QUESTIONS_DIR": str(tmp_path),
        **overrides,
    }
    return prov.ProvisionSettings.from_env(env)


def body(call):
    return json.loads(call.request.body)


def test_settings_require_credentials():
    with pytest.raises(ValueError, match="METABASE_ADMIN_EMAIL"):
        prov.ProvisionSettings.from_env({})


def test_settings_default_to_the_compose_network(tmp_path):
    s = settings(tmp_path)
    assert (s.warehouse_host, s.warehouse_port) == ("postgres", 5432)


@responses.activate
def test_login_runs_first_time_setup():
    responses.get(
        f"{URL}/api/session/properties", json={"has-user-setup": False, "setup-token": "tok"}
    )
    setup = responses.post(f"{URL}/api/setup", json={"id": "setup-session"})
    responses.post(f"{URL}/api/session", json={"id": "session-1"})

    mb = Metabase(URL)
    mb.login("admin@example.com", "secret-1", "Public spend")

    assert body(setup.calls[0])["token"] == "tok"
    assert body(setup.calls[0])["user"]["email"] == "admin@example.com"
    assert mb.http.headers["X-Metabase-Session"] == "session-1"


@responses.activate
def test_login_skips_setup_when_done():
    responses.get(f"{URL}/api/session/properties", json={"has-user-setup": True})
    responses.post(f"{URL}/api/session", json={"id": "session-1"})

    Metabase(URL).login("admin@example.com", "secret-1", "Public spend")

    assert [c.request.url for c in responses.calls][-1] == f"{URL}/api/session"


@responses.activate
def test_errors_include_status_and_body():
    responses.get(f"{URL}/api/database", status=403, body="nope")
    with pytest.raises(MetabaseError, match="403: nope"):
        Metabase(URL).list_databases()


@responses.activate
def test_database_is_created_then_updated(tmp_path):
    s = settings(tmp_path)
    mb = Metabase(URL)
    responses.get(f"{URL}/api/database", json={"data": []})
    create = responses.post(f"{URL}/api/database", json={"id": 7})
    responses.post(f"{URL}/api/database/7/sync_schema", json={})

    assert prov.upsert_database(mb, s) == 7
    details = body(create.calls[0])["details"]
    assert details["user"] == "bi_reader"
    assert details["schema-filters-patterns"] == "marts"

    responses.replace(
        responses.GET, f"{URL}/api/database", json={"data": [{"id": 7, "name": prov.DATABASE_NAME}]}
    )
    update = responses.put(f"{URL}/api/database/7", json={})
    assert prov.upsert_database(mb, s) == 7
    assert len(update.calls) == 1
    assert len(create.calls) == 1


@responses.activate
def test_cards_are_matched_by_name_and_stale_ones_archived(tmp_path):
    s = settings(tmp_path)
    mb = Metabase(URL)
    kept = QUESTIONS[0]
    responses.get(
        f"{URL}/api/collection/3/items",
        json={"data": [{"id": 10, "name": kept.name}, {"id": 11, "name": "Old question"}]},
    )
    update = responses.put(f"{URL}/api/card/10", json={})
    archive = responses.put(f"{URL}/api/card/11", json={})
    create = responses.post(f"{URL}/api/card", json={"id": 99})

    card_ids = prov.upsert_cards(mb, s.questions_dir, database_id=7, collection_id=3)

    assert card_ids[kept.key] == 10
    assert body(update.calls[0])["dataset_query"]["native"]["query"] == f"select 1 as {kept.key}"
    assert body(update.calls[0])["dataset_query"]["database"] == 7
    assert len(create.calls) == len(QUESTIONS) - 1
    assert body(archive.calls[0]) == {"archived": True}


def test_text_tiles_become_virtual_cards():
    tile = prov.Tile(0, 0, 24, 2, text="## Title")
    card = prov.dashcard(0, tile, {})
    assert card["id"] == -1
    assert card["card_id"] is None
    assert card["visualization_settings"]["text"] == "## Title"

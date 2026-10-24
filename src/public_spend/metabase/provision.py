"""Provision Metabase: admin user, warehouse connection, questions, dashboards.

Idempotent: objects are matched by name and updated in place, so re-running
after editing a question's SQL or a dashboard layout applies the change.

    python -m public_spend.metabase.provision
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from public_spend.metabase.client import Metabase
from public_spend.metabase.content import DASHBOARDS, QUESTIONS, Dashboard, Question, Tile

log = logging.getLogger(__name__)

SITE_NAME = "Public spend"
DATABASE_NAME = "Public spend warehouse"
COLLECTION_NAME = "Public spend"
DEFAULT_QUESTIONS_DIR = Path(__file__).resolve().parents[3] / "bi" / "metabase" / "questions"


@dataclass(frozen=True)
class ProvisionSettings:
    metabase_url: str
    admin_email: str
    admin_password: str
    warehouse_host: str
    warehouse_port: int
    warehouse_db: str
    reader_user: str
    reader_password: str
    questions_dir: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ProvisionSettings:
        env = os.environ if env is None else env

        def required(name: str) -> str:
            value = env.get(name)
            if not value:
                raise ValueError(f"{name} is required")
            return value

        return cls(
            metabase_url=env.get("METABASE_URL", "http://localhost:3000"),
            admin_email=required("METABASE_ADMIN_EMAIL"),
            admin_password=required("METABASE_ADMIN_PASSWORD"),
            # Host and port as seen from the Metabase container, not from the caller.
            warehouse_host=env.get("METABASE_WAREHOUSE_HOST", "postgres"),
            warehouse_port=int(env.get("METABASE_WAREHOUSE_PORT", "5432")),
            warehouse_db=required("WAREHOUSE_DB"),
            reader_user=required("BI_READER_USER"),
            reader_password=required("BI_READER_PASSWORD"),
            questions_dir=Path(env.get("METABASE_QUESTIONS_DIR", DEFAULT_QUESTIONS_DIR)),
        )


def upsert_database(mb: Metabase, settings: ProvisionSettings) -> int:
    payload = {
        "engine": "postgres",
        "name": DATABASE_NAME,
        "details": {
            "host": settings.warehouse_host,
            "port": settings.warehouse_port,
            "dbname": settings.warehouse_db,
            "user": settings.reader_user,
            "password": settings.reader_password,
            "ssl": False,
            # Only the marts are exposed; the reader cannot see other schemas anyway.
            "schema-filters-type": "inclusion",
            "schema-filters-patterns": "marts",
        },
    }
    existing = next((db for db in mb.list_databases() if db["name"] == DATABASE_NAME), None)
    if existing:
        mb.put(f"database/{existing['id']}", payload)
        database_id = existing["id"]
    else:
        database_id = mb.post("database", payload)["id"]
    mb.post(f"database/{database_id}/sync_schema")
    return database_id


def upsert_collection(mb: Metabase) -> int:
    for collection in mb.get("collection"):
        if (
            collection.get("name") == COLLECTION_NAME
            and not collection.get("archived")
            and collection.get("personal_owner_id") is None
        ):
            return collection["id"]
    created = mb.post(
        "collection",
        {"name": COLLECTION_NAME, "description": "Dashboards provisioned from bi/metabase."},
    )
    return created["id"]


def card_payload(
    question: Question, sql: str, database_id: int, collection_id: int
) -> dict[str, Any]:
    return {
        "name": question.name,
        "description": question.description or None,
        "display": question.display,
        "visualization_settings": question.visualization_settings(),
        "collection_id": collection_id,
        "dataset_query": {
            "type": "native",
            "database": database_id,
            "native": {"query": sql, "template-tags": {}},
        },
    }


def upsert_cards(
    mb: Metabase, questions_dir: Path, database_id: int, collection_id: int
) -> dict[str, int]:
    existing = {item["name"]: item["id"] for item in mb.collection_items(collection_id, "card")}
    card_ids = {}
    for question in QUESTIONS:
        sql = (questions_dir / f"{question.key}.sql").read_text(encoding="utf-8")
        payload = card_payload(question, sql, database_id, collection_id)
        if question.name in existing:
            card_id = existing[question.name]
            mb.put(f"card/{card_id}", payload)
        else:
            card_id = mb.post("card", payload)["id"]
        card_ids[question.key] = card_id
    # Questions removed from the code are archived, not left behind.
    for name, card_id in existing.items():
        if name not in {question.name for question in QUESTIONS}:
            mb.put(f"card/{card_id}", {"archived": True})
    return card_ids


def dashcard(index: int, tile: Tile, card_ids: Mapping[str, int]) -> dict[str, Any]:
    base = {
        # Negative ids create new dashcards; the ones not listed are removed.
        "id": -(index + 1),
        "row": tile.row,
        "col": tile.col,
        "size_x": tile.width,
        "size_y": tile.height,
        "parameter_mappings": [],
    }
    if tile.text is not None:
        return base | {
            "card_id": None,
            "visualization_settings": {
                "virtual_card": {
                    "name": None,
                    "display": "text",
                    "visualization_settings": {},
                    "dataset_query": {},
                    "archived": False,
                },
                "text": tile.text,
            },
        }
    return base | {"card_id": card_ids[tile.question], "visualization_settings": {}}


def upsert_dashboard(
    mb: Metabase, dashboard: Dashboard, collection_id: int, card_ids: Mapping[str, int]
) -> int:
    items = mb.collection_items(collection_id, "dashboard")
    dashboard_id = next((item["id"] for item in items if item["name"] == dashboard.name), None)
    if dashboard_id is None:
        dashboard_id = mb.post(
            "dashboard", {"name": dashboard.name, "collection_id": collection_id}
        )["id"]
    mb.put(
        f"dashboard/{dashboard_id}",
        {
            "description": dashboard.description,
            "width": "full",
            "dashcards": [
                dashcard(index, tile, card_ids) for index, tile in enumerate(dashboard.tiles)
            ],
        },
    )
    return dashboard_id


def provision(settings: ProvisionSettings, mb: Metabase | None = None) -> dict[str, int]:
    mb = mb or Metabase(settings.metabase_url)
    mb.wait_until_healthy()
    mb.login(settings.admin_email, settings.admin_password, SITE_NAME)
    database_id = upsert_database(mb, settings)
    collection_id = upsert_collection(mb)
    card_ids = upsert_cards(mb, settings.questions_dir, database_id, collection_id)
    dashboards = {
        dashboard.name: upsert_dashboard(mb, dashboard, collection_id, card_ids)
        for dashboard in DASHBOARDS
    }
    log.info(
        "provisioned database %s, %d questions and dashboards %s",
        database_id,
        len(card_ids),
        dashboards,
    )
    return dashboards


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    provision(ProvisionSettings.from_env())


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import uuid
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest


@pytest.fixture
def make_bundle(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Build a ZIP shaped like an OECE monthly bundle from ``{member: csv_text}``."""

    def _make(files: dict[str, str], name: str = "bundle.zip") -> Path:
        path = tmp_path / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for member, text in files.items():
                archive.writestr(member, text.encode("utf-8"))
        return path

    return _make


@pytest.fixture
def pg_dsn() -> str:
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is not set")
    return dsn


@pytest.fixture
def pg_conn(pg_dsn: str):
    from public_spend.db import connect

    with connect(pg_dsn) as conn:
        yield conn


@pytest.fixture
def raw_schema(pg_conn) -> Iterator[str]:
    """A throwaway schema, dropped after the test."""
    schema = f"test_raw_{uuid.uuid4().hex[:8]}"
    yield schema
    pg_conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

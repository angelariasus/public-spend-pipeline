"""Conditional download of the MEF investment CSV and header parsing."""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import requests

_COLUMN_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_CHUNK_SIZE = 1024 * 1024

# A response without these columns is not the dataset (e.g. an HTML error page).
REQUIRED_COLUMNS: tuple[str, ...] = ("codigo_unico", "entidad", "nivel")


class SourceError(Exception):
    """The downloaded file is not the expected dataset."""


@dataclass(frozen=True)
class Download:
    path: Path
    sha256: str
    etag: str | None
    last_modified: str | None


def download(
    session: requests.Session,
    url: str,
    dest: Path,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout: int = 120,
) -> Download | None:
    """Download ``url`` to ``dest`` unless the server reports it unchanged.

    Sends the validators from the previous load; returns ``None`` on HTTP 304.
    The file is hashed while it is written, so a server that ignores the
    validators is still caught by comparing content hashes.
    """
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    digest = hashlib.sha256()
    with session.get(url, headers=headers, stream=True, timeout=timeout) as response:
        if response.status_code == 304:
            return None
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                fh.write(chunk)
                digest.update(chunk)
        return Download(
            path=dest,
            sha256=digest.hexdigest(),
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )


def read_columns(path: Path) -> list[str]:
    """Return the CSV header as lowercase column names, validated for use in SQL."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh), [])

    columns = [name.strip().lower() for name in header]
    invalid = [name for name in columns if not _COLUMN_RE.match(name)]
    if invalid:
        raise SourceError(f"unexpected column names: {invalid[:5]}")
    if len(set(columns)) != len(columns):
        raise SourceError("duplicate column names in header")
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise SourceError(f"required columns missing: {missing}")
    return columns

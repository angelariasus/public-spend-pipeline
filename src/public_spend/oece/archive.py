"""Download and read the monthly OCDS CSV bundle (a ZIP with one CSV per table)."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path, PurePosixPath

import requests

_TABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_CHUNK_SIZE = 1024 * 1024

# Some OCDS text fields (tender descriptions, addresses) exceed the csv default.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


class ArchiveError(Exception):
    """The downloaded bundle is not what we expected."""


def download(session: requests.Session, url: str, dest: Path, timeout: int = 120) -> Path:
    """Stream ``url`` to ``dest`` and check that the result is a ZIP file."""
    with session.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                fh.write(chunk)
    if not zipfile.is_zipfile(dest):
        raise ArchiveError(f"{url} did not return a ZIP file")
    return dest


def table_name(member: str) -> str:
    """Map a ZIP member such as ``com_awa_ite_additionalClassific.csv`` to a table name."""
    name = PurePosixPath(member).stem.lower()
    if not _TABLE_NAME_RE.match(name):
        raise ArchiveError(f"unexpected file name in bundle: {member!r}")
    return name


def find_members(zip_path: Path, tables: Iterable[str]) -> dict[str, str]:
    """Return ``{table_name: member_name}`` for the requested tables present in the bundle."""
    wanted = set(tables)
    with zipfile.ZipFile(zip_path) as archive:
        members = {
            table_name(info.filename): info.filename
            for info in archive.infolist()
            if info.filename.lower().endswith(".csv")
        }
    return {name: member for name, member in sorted(members.items()) if name in wanted}


def content_sha256(zip_path: Path, members: dict[str, str]) -> str:
    """Hash the uncompressed content of the selected members.

    The portal regenerates every monthly bundle daily, so neither the index
    timestamp nor the ZIP bytes reveal whether the data changed. Hashing the
    CSV content does.
    """
    digest = hashlib.sha256()
    with zipfile.ZipFile(zip_path) as archive:
        for name in sorted(members):
            digest.update(name.encode() + b"\0")
            with archive.open(members[name]) as fh:
                while chunk := fh.read(_CHUNK_SIZE):
                    digest.update(chunk)
    return digest.hexdigest()


def iter_rows(zip_path: Path, member: str) -> Iterator[dict[str, str]]:
    """Yield each CSV row as a dict, omitting empty values.

    CSV cannot tell an empty string from a missing value; dropping empty
    cells keeps the raw JSON compact, and ``data->>'column'`` still returns
    NULL for them downstream.
    """
    with zipfile.ZipFile(zip_path) as archive, archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        for row in reader:
            if None in row:
                raise ArchiveError(
                    f"{member}: line {reader.line_num} has more fields than the header"
                )
            yield {key: value for key, value in row.items() if value not in ("", None)}

"""Client for the OECE bulk file index (``GET /files``).

The index lists one entry per source and month, each with download URLs for
several formats. It is paginated (5 entries per page).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import requests

from public_spend.config import Period

_MAX_PAGES = 1_000


@dataclass(frozen=True)
class FileEntry:
    source: str
    period: Period
    csv_url: str
    published_at: str

    def to_dict(self) -> dict[str, str]:
        """Serialize to plain strings (safe to pass between Airflow tasks)."""
        data = asdict(self)
        data["period"] = str(self.period)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> FileEntry:
        return cls(
            source=data["source"],
            period=Period.parse(data["period"]),
            csv_url=data["csv_url"],
            published_at=data["published_at"],
        )


def fetch_index(session: requests.Session, base_url: str, timeout: int = 60) -> list[FileEntry]:
    """Walk every page of the file index and return all entries."""
    entries: list[FileEntry] = []
    page: int | None = 1
    for _ in range(_MAX_PAGES):
        if page is None:
            return entries
        response = session.get(
            f"{base_url}/files",
            params={"page": page},
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        entries.extend(_parse_entry(item) for item in payload["results"])
        page = payload["pagination"]["next_page_number"]
    raise RuntimeError(f"file index has more than {_MAX_PAGES} pages; refusing to continue")


def _parse_entry(item: dict) -> FileEntry:
    return FileEntry(
        source=item["source"],
        period=Period(int(item["year"]), int(item["month"])),
        csv_url=item["files"]["csv"],
        published_at=item["timestamp"],
    )


def select_entries(
    entries: list[FileEntry],
    source: str,
    start: Period,
    end: Period | None = None,
) -> list[FileEntry]:
    """Keep entries of ``source`` within ``[start, end]``, oldest first."""
    selected = [
        entry
        for entry in entries
        if entry.source == source and entry.period >= start and (end is None or entry.period <= end)
    ]
    return sorted(selected, key=lambda entry: entry.period)

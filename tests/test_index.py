import responses

from public_spend.config import Period
from public_spend.http import build_session
from public_spend.oece.index import FileEntry, fetch_index, select_entries

BASE = "https://example.org/api/v1"


def _item(source: str, year: str, month: str) -> dict:
    return {
        "id": f"{source}-{year}-{month}",
        "source": source,
        "year": year,
        "month": month,
        "timestamp": "2026-10-23T14:27:08-05:00",
        "files": {"csv": f"{BASE}/file/{source}/csv/{year}/{month}/"},
    }


def _page(items: list[dict], next_page: int | None) -> dict:
    return {"results": items, "pagination": {"next_page_number": next_page}}


@responses.activate
def test_fetch_index_follows_pagination():
    responses.get(
        f"{BASE}/files",
        match=[responses.matchers.query_param_matcher({"page": "1"})],
        json=_page([_item("seace_v3", "2026", "10")], next_page=2),
    )
    responses.get(
        f"{BASE}/files",
        match=[responses.matchers.query_param_matcher({"page": "2"})],
        json=_page([_item("seace_v2", "2017", "08")], next_page=None),
    )

    entries = fetch_index(build_session("test-agent", retries=0), BASE)

    assert [(e.source, str(e.period)) for e in entries] == [
        ("seace_v3", "2026-10"),
        ("seace_v2", "2017-08"),
    ]
    assert entries[0].csv_url == f"{BASE}/file/seace_v3/csv/2026/10/"
    assert responses.calls[0].request.headers["User-Agent"] == "test-agent"


def _entry(source: str, year: int, month: int) -> FileEntry:
    return FileEntry(source, Period(year, month), "url", "ts")


def test_select_entries_filters_source_and_range_and_sorts():
    entries = [
        _entry("seace_v3", 2026, 10),
        _entry("seace_v3", 2023, 12),
        _entry("seace_v2", 2024, 5),
        _entry("seace_v3", 2024, 1),
        _entry("seace_v3", 2025, 6),
    ]

    selected = select_entries(entries, "seace_v3", Period(2024, 1), Period(2025, 6))

    assert [str(e.period) for e in selected] == ["2024-01", "2025-06"]


def test_select_entries_without_end_keeps_latest():
    entries = [_entry("seace_v3", 2026, 10), _entry("seace_v3", 2024, 2)]
    selected = select_entries(entries, "seace_v3", Period(2024, 1))
    assert [str(e.period) for e in selected] == ["2024-02", "2026-10"]


def test_file_entry_round_trip():
    entry = _entry("seace_v3", 2024, 3)
    assert FileEntry.from_dict(entry.to_dict()) == entry

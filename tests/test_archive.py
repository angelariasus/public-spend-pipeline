import pytest
import responses

from public_spend.http import build_session
from public_spend.oece.archive import (
    ArchiveError,
    content_sha256,
    download,
    find_members,
    iter_rows,
    table_name,
)

RECORDS = "ocid,compiledRelease/buyer/name,compiledRelease/planning/budget/projectID\n"


def test_table_name_lowercases_stem():
    assert table_name("com_awa_ite_additionalClassific.csv") == "com_awa_ite_additionalclassific"
    assert table_name("folder/records.csv") == "records"


def test_table_name_rejects_unsafe_names():
    with pytest.raises(ArchiveError):
        table_name("records; DROP TABLE x.csv")


def test_find_members_keeps_only_requested_tables(make_bundle):
    bundle = make_bundle({"records.csv": RECORDS, "releases.csv": "a\n", "com_Awards.csv": "a\n"})
    assert find_members(bundle, ["records", "com_awards", "com_contracts"]) == {
        "com_awards": "com_Awards.csv",
        "records": "records.csv",
    }


def test_iter_rows_drops_empty_values_and_handles_bom(make_bundle):
    text = "﻿" + RECORDS + 'ocds-1,"MUNICIPALIDAD DE CUSCO, SEDE",2387471\nocds-2,ENTIDAD Ñ,\n'
    bundle = make_bundle({"records.csv": text})

    rows = list(iter_rows(bundle, "records.csv"))

    assert rows == [
        {
            "ocid": "ocds-1",
            "compiledRelease/buyer/name": "MUNICIPALIDAD DE CUSCO, SEDE",
            "compiledRelease/planning/budget/projectID": "2387471",
        },
        {"ocid": "ocds-2", "compiledRelease/buyer/name": "ENTIDAD Ñ"},
    ]


def test_iter_rows_rejects_rows_longer_than_header(make_bundle):
    bundle = make_bundle({"records.csv": "a,b\n1,2,3\n"})
    with pytest.raises(ArchiveError, match="line 2"):
        list(iter_rows(bundle, "records.csv"))


def test_content_sha256_ignores_unselected_tables(make_bundle):
    a = make_bundle({"records.csv": RECORDS, "releases.csv": "x\n"}, name="a.zip")
    b = make_bundle({"records.csv": RECORDS, "releases.csv": "y\n"}, name="b.zip")
    c = make_bundle({"records.csv": RECORDS + "ocds-9,,\n"}, name="c.zip")

    members = {"records": "records.csv"}
    assert content_sha256(a, members) == content_sha256(b, members)
    assert content_sha256(a, members) != content_sha256(c, members)


@responses.activate
def test_download_writes_zip(tmp_path, make_bundle):
    payload = make_bundle({"records.csv": RECORDS}).read_bytes()
    responses.get("https://example.org/file.zip", body=payload)

    dest = download(
        build_session("ua", retries=0), "https://example.org/file.zip", tmp_path / "f.zip"
    )

    assert dest.read_bytes() == payload


@responses.activate
def test_download_rejects_non_zip(tmp_path):
    responses.get("https://example.org/file.zip", body="<html>blocked</html>")
    with pytest.raises(ArchiveError):
        download(build_session("ua", retries=0), "https://example.org/file.zip", tmp_path / "f.zip")

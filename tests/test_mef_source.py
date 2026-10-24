import hashlib

import pytest
import responses

from public_spend.http import build_session
from public_spend.mef.source import SourceError, download, read_columns

URL = "https://example.org/DETALLE_INVERSIONES.csv"
CSV = '﻿"NIVEL","ENTIDAD","CODIGO_UNICO"\n"GL","MUNICIPALIDAD A","2387471"\n'


@responses.activate
def test_download_returns_file_hash_and_validators(tmp_path):
    responses.get(URL, body=CSV.encode(), headers={"ETag": '"abc"', "Last-Modified": "Thu, 22 Oct"})

    result = download(build_session("ua", retries=0), URL, tmp_path / "f.csv")

    assert result.path.read_bytes() == CSV.encode()
    assert result.sha256 == hashlib.sha256(CSV.encode()).hexdigest()
    assert (result.etag, result.last_modified) == ('"abc"', "Thu, 22 Oct")


@responses.activate
def test_download_sends_validators_and_returns_none_when_not_modified(tmp_path):
    responses.get(
        URL,
        status=304,
        match=[
            responses.matchers.header_matcher(
                {"If-None-Match": '"abc"', "If-Modified-Since": "Thu, 22 Oct"}
            )
        ],
    )

    result = download(
        build_session("ua", retries=0),
        URL,
        tmp_path / "f.csv",
        etag='"abc"',
        last_modified="Thu, 22 Oct",
    )

    assert result is None
    assert not (tmp_path / "f.csv").exists()


def test_read_columns_lowercases_and_strips_bom(tmp_path):
    path = tmp_path / "f.csv"
    path.write_text(CSV, encoding="utf-8")
    assert read_columns(path) == ["nivel", "entidad", "codigo_unico"]


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ("<html><body>error</body></html>\n", "unexpected column names"),
        ("NIVEL,ENTIDAD,CODIGO_UNICO,nivel\n", "duplicate"),
        ("NIVEL,ENTIDAD\n", "required columns missing"),
    ],
)
def test_read_columns_rejects_unexpected_files(tmp_path, header, message):
    path = tmp_path / "f.csv"
    path.write_text(header, encoding="utf-8")
    with pytest.raises(SourceError, match=message):
        read_columns(path)

"""Shared HTTP session with retries."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(
    user_agent: str, retries: int = 5, backoff_factor: float = 2.0
) -> requests.Session:
    """Return a session that retries transient failures with exponential backoff.

    Government portals in Peru reject requests without a browser-like
    User-Agent (HTTP 418), so one is always sent.
    """
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

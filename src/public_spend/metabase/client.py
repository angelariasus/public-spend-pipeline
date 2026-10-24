"""Minimal client for the Metabase REST API."""

from __future__ import annotations

import time
from typing import Any

import requests


class MetabaseError(RuntimeError):
    pass


class Metabase:
    def __init__(self, url: str, session: requests.Session | None = None, timeout: int = 60):
        self.url = url.rstrip("/")
        self.http = session or requests.Session()
        self.timeout = timeout

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.http.request(
            method, f"{self.url}/api/{path.lstrip('/')}", timeout=self.timeout, **kwargs
        )
        if not response.ok:
            raise MetabaseError(
                f"{method} /api/{path} returned {response.status_code}: {response.text[:500]}"
            )
        return response.json() if response.content else None

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PUT", path, json=payload)

    def wait_until_healthy(self, timeout_seconds: int = 300, poll_seconds: float = 5) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                response = self.http.get(f"{self.url}/api/health", timeout=10)
                if response.ok and response.json().get("status") == "ok":
                    return
            except requests.RequestException:
                pass
            if time.monotonic() > deadline:
                raise MetabaseError(f"Metabase at {self.url} not healthy after {timeout_seconds}s")
            time.sleep(poll_seconds)

    def login(self, email: str, password: str, site_name: str) -> None:
        """Log in, completing the first-run setup with this account if needed."""
        properties = self.get("session/properties")
        if not properties.get("has-user-setup"):
            self.post(
                "setup",
                {
                    "token": properties["setup-token"],
                    "user": {
                        "email": email,
                        "password": password,
                        "first_name": "Admin",
                        "last_name": "Public spend",
                        "site_name": site_name,
                    },
                    "prefs": {"site_name": site_name, "site_locale": "en", "allow_tracking": False},
                },
            )
        session = self.post("session", {"username": email, "password": password})
        self.http.headers["X-Metabase-Session"] = session["id"]

    def list_databases(self) -> list[dict[str, Any]]:
        databases = self.get("database")
        # Newer versions wrap lists in {"data": [...], "total": n}.
        return databases["data"] if isinstance(databases, dict) else databases

    def collection_items(self, collection_id: int, model: str) -> list[dict[str, Any]]:
        items = self.get(f"collection/{collection_id}/items", params={"models": model})
        return items["data"] if isinstance(items, dict) else items

"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")

# OCDS tables loaded by default. The monthly bundle ships 21 CSVs; documents
# and the full release history are not needed downstream. Exchange rates are:
# about 2% of awards and contracts are not in soles.
DEFAULT_OECE_TABLES: tuple[str, ...] = (
    "records",
    "com_parties",
    "com_ten_items",
    "com_ten_ite_additionalclassific",
    "com_ten_tenderers",
    "com_awards",
    "com_awa_suppliers",
    "com_awa_val_exchangerates",
    "com_contracts",
    "com_con_val_exchangerates",
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass(frozen=True, order=True)
class Period:
    """A calendar month, e.g. ``Period(2024, 1)`` for January 2024."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError(f"month must be between 1 and 12, got {self.month}")

    @classmethod
    def parse(cls, value: str) -> Period:
        match = _PERIOD_RE.match(value.strip())
        if not match:
            raise ValueError(f"expected a period formatted as YYYY-MM, got {value!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class Settings:
    warehouse_dsn: str
    oece_start_period: Period
    oece_end_period: Period | None = None
    oece_base_url: str = "https://contratacionesabiertas.oece.gob.pe/api/v1"
    oece_source: str = "seace_v3"
    oece_tables: tuple[str, ...] = DEFAULT_OECE_TABLES
    mef_investments_url: str = (
        "https://fs.datosabiertos.mef.gob.pe/datastorefiles/DETALLE_INVERSIONES.csv"
    )
    mef_closed_investments_url: str = (
        "https://fs.datosabiertos.mef.gob.pe/datastorefiles/CIERRE_INVERSIONES.csv"
    )
    raw_schema: str = "raw"
    user_agent: str = DEFAULT_USER_AGENT
    http_timeout_seconds: int = 120

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env

        dsn = env.get("WAREHOUSE_DSN", "").strip()
        if not dsn:
            raise ValueError("WAREHOUSE_DSN is not set")

        end = env.get("OECE_END_PERIOD", "").strip()
        tables = env.get("OECE_TABLES", "").strip()

        return cls(
            warehouse_dsn=dsn,
            oece_start_period=Period.parse(env.get("OECE_START_PERIOD", "2024-01")),
            oece_end_period=Period.parse(end) if end else None,
            oece_base_url=env.get("OECE_BASE_URL", cls.oece_base_url).rstrip("/"),
            oece_source=env.get("OECE_SOURCE", cls.oece_source),
            oece_tables=(
                tuple(t.strip().lower() for t in tables.split(",") if t.strip())
                if tables
                else DEFAULT_OECE_TABLES
            ),
            mef_investments_url=env.get("MEF_INVESTMENTS_URL", cls.mef_investments_url),
            mef_closed_investments_url=env.get(
                "MEF_CLOSED_INVESTMENTS_URL", cls.mef_closed_investments_url
            ),
            raw_schema=env.get("RAW_SCHEMA", cls.raw_schema),
            user_agent=env.get("HTTP_USER_AGENT", cls.user_agent),
            http_timeout_seconds=int(
                env.get("HTTP_TIMEOUT_SECONDS", str(cls.http_timeout_seconds))
            ),
        )

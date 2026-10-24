"""Questions and dashboards provisioned in Metabase.

Each question's SQL lives in ``bi/metabase/questions/<key>.sql`` and reads only
the ``marts`` schema. Dashboards are laid out on Metabase's 24-column grid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

GRID_WIDTH = 24

# Human-readable column titles, shared by every question that returns the column.
COLUMN_TITLES = {
    "awarded_amount_pen": "Awarded (S/)",
    "awarded_millions_pen": "Awarded (S/ millions)",
    "contracted_amount_pen": "Contracted (S/)",
    "contracted_millions_pen": "Contracted (S/ millions)",
    "accrued_millions_pen": "Accrued spend (S/ millions)",
    "accrued_total": "Accrued spend (S/)",
    "updated_cost": "Updated cost (S/)",
    "contracted_to_cost_pct": "Contracted / cost (%)",
    "physical_progress_pct": "Physical progress (%)",
    "month_start": "Month",
    "category": "Category",
    "entity_name": "Entity",
    "department": "Department",
    "supplier_type": "Supplier type",
    "award_year": "Year",
    "concentration_level": "Concentration",
    "entities": "Entities",
    "supplier_count": "Suppliers",
    "top_supplier_name": "Top supplier",
    "top_supplier_share": "Top supplier share",
    "hhi": "HHI",
    "government_level": "Level of government",
    "physical_progress": "Physical progress",
    "projects": "Projects",
    "project_code": "Project code",
    "project_name": "Project",
    "first_contract_signed_on": "First contract signed",
    "process_count": "Processes",
}


def columns(**settings_by_column: dict[str, Any]) -> dict[str, Any]:
    return {
        "column_settings": {
            json.dumps(["name", name]): value for name, value in settings_by_column.items()
        }
    }


def soles(*names: str) -> dict[str, Any]:
    return columns(**{name: {"prefix": "S/ ", "decimals": 0} for name in names})


def percent(*names: str) -> dict[str, Any]:
    return columns(**{name: {"number_style": "percent", "decimals": 1} for name in names})


def merge(*settings: dict[str, Any]) -> dict[str, Any]:
    """Combine visualization settings, merging the settings of each column."""
    merged: dict[str, Any] = {"column_settings": {}}
    for item in settings:
        merged |= {key: value for key, value in item.items() if key != "column_settings"}
        for column, value in item.get("column_settings", {}).items():
            merged["column_settings"][column] = merged["column_settings"].get(column, {}) | value
    return merged


def chart(
    dimensions: list[str], metrics: list[str], y_title: str | None = None, **extra: Any
) -> dict[str, Any]:
    """Bar, line or row chart settings; axis titles default to the column titles."""
    return {
        "graph.dimensions": dimensions,
        "graph.metrics": metrics,
        "graph.x_axis.title_text": COLUMN_TITLES.get(dimensions[0], dimensions[0]),
        "graph.y_axis.title_text": y_title or COLUMN_TITLES.get(metrics[0], metrics[0]),
        **extra,
    }


@dataclass(frozen=True)
class Question:
    key: str
    name: str
    display: str
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    def visualization_settings(self) -> dict[str, Any]:
        """Settings with readable titles for every known column."""
        titles = columns(**{name: {"column_title": title} for name, title in COLUMN_TITLES.items()})
        return merge(titles, self.settings)


@dataclass(frozen=True)
class Tile:
    row: int
    col: int
    width: int
    height: int
    question: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class Dashboard:
    name: str
    description: str
    tiles: tuple[Tile, ...]


STACKED = {"stackable.stack_type": "stacked"}
CONCENTRATION_COLORS = {
    "series_settings": {
        "low": {"color": "#88BF4D"},
        "moderate": {"color": "#F9CF48"},
        "high": {"color": "#EF8C8C"},
    }
}

QUESTIONS = (
    # Procurement overview
    Question(
        "awarded_amount",
        "Awarded amount",
        "scalar",
        "All awards, in soles.",
        soles("awarded_amount_pen"),
    ),
    Question("process_count", "Contracting processes", "scalar"),
    Question("supplier_count", "Suppliers with awards", "scalar"),
    Question(
        "foreign_currency_share",
        "Awarded in foreign currency",
        "scalar",
        "Share of the awarded amount originally in USD, EUR or other currencies.",
        percent("foreign_currency_share"),
    ),
    Question(
        "awarded_by_month",
        "Awarded amount by month and category",
        "bar",
        "Only processes published since January 2024 are loaded, so the first months ramp up.",
        chart(["month_start", "category"], ["awarded_millions_pen"], **STACKED),
    ),
    Question(
        "top_entities",
        "Top 15 entities by awarded amount",
        "row",
        settings=chart(["entity_name"], ["awarded_millions_pen"]),
    ),
    Question(
        "awarded_by_department",
        "Awarded amount by department of the buyer",
        "row",
        settings=chart(["department"], ["awarded_millions_pen"]),
    ),
    Question(
        "awarded_by_supplier_type",
        "Awarded amount by supplier type",
        "pie",
        settings=merge(
            {"pie.dimension": "supplier_type", "pie.metric": "awarded_amount_pen"},
            soles("awarded_amount_pen"),
        ),
    ),
    Question(
        "concentration_levels",
        "Entities by supplier concentration (HHI)",
        "bar",
        "Low: HHI < 1,500. Moderate: < 2,500. High: 2,500 or more.",
        chart(
            ["award_year", "concentration_level"],
            ["entities"],
            **STACKED,
            **CONCENTRATION_COLORS,
        ),
    ),
    Question(
        "concentrated_buyers",
        "Most concentrated entities (S/ 10M+ awarded in the year)",
        "table",
        settings=merge(soles("awarded_amount_pen"), percent("top_supplier_share")),
    ),
    # Investment versus procurement
    Question(
        "linked_projects",
        "Investment projects with contracts",
        "scalar",
        "Projects funded by a SEACE process and found in the MEF files.",
    ),
    Question(
        "contracted_amount",
        "Contracted for investment projects",
        "scalar",
        settings=soles("contracted_amount_pen"),
    ),
    Question(
        "lagging_project_count",
        "Lagging projects",
        "scalar",
        "Active, S/ 1M+ contracted over a year ago, under 25% physical progress.",
    ),
    Question(
        "lagging_contracted_amount",
        "Contracted in lagging projects",
        "scalar",
        settings=soles("contracted_amount_pen"),
    ),
    Question(
        "contracted_vs_accrued_by_level",
        "Contracted vs accrued spend by level of government",
        "bar",
        "GN: national, GR: regional, GL: local. Accrued spend covers the whole project life.",
        chart(
            ["government_level"],
            ["contracted_millions_pen", "accrued_millions_pen"],
            y_title="S/ millions",
            series_settings={
                "contracted_millions_pen": {"title": "Contracted"},
                "accrued_millions_pen": {"title": "Accrued spend"},
            },
        ),
    ),
    Question(
        "progress_distribution",
        "Physical progress of active projects with S/ 1M+ contracted",
        "bar",
        settings=chart(["physical_progress"], ["projects"]),
    ),
    Question(
        "contracted_by_department",
        "Contracted amount by department of the project",
        "row",
        settings=chart(["department"], ["contracted_millions_pen"]),
    ),
    Question(
        "lagging_projects",
        "Lagging projects with the largest contracts",
        "table",
        settings=soles("contracted_amount_pen", "updated_cost", "accrued_total"),
    ),
    Question(
        "contracted_above_cost",
        "Contracts above 150% of the project cost",
        "table",
        "Usually processes tagged with the wrong project code, or costs never updated in MEF.",
        soles("contracted_amount_pen", "updated_cost"),
    ),
)

DASHBOARDS = (
    Dashboard(
        "Public procurement overview",
        "Awards in SEACE (OECE open contracting data), converted to soles.",
        (
            Tile(
                0,
                0,
                24,
                2,
                text=(
                    "## Public procurement in Peru\n"
                    "Awards of processes published by OECE (SEACE) since January 2024. "
                    "Foreign-currency amounts are converted to soles with the rate reported "
                    "by each record or the month's average."
                ),
            ),
            Tile(2, 0, 6, 3, "awarded_amount"),
            Tile(2, 6, 6, 3, "process_count"),
            Tile(2, 12, 6, 3, "supplier_count"),
            Tile(2, 18, 6, 3, "foreign_currency_share"),
            Tile(5, 0, 24, 7, "awarded_by_month"),
            Tile(12, 0, 12, 9, "top_entities"),
            Tile(12, 12, 12, 9, "awarded_by_department"),
            Tile(21, 0, 8, 7, "awarded_by_supplier_type"),
            Tile(21, 8, 16, 7, "concentration_levels"),
            Tile(28, 0, 24, 9, "concentrated_buyers"),
        ),
    ),
    Dashboard(
        "Investment projects: contracted vs delivered",
        "SEACE contracts linked to MEF public investment projects by project code.",
        (
            Tile(
                0,
                0,
                24,
                2,
                text=(
                    "## Contracted vs delivered\n"
                    "Contracts signed through SEACE for each MEF investment project, next to "
                    "what MEF reports as accrued spend and physical progress. Processes that "
                    "fund several projects are split equally among them."
                ),
            ),
            Tile(2, 0, 6, 3, "linked_projects"),
            Tile(2, 6, 6, 3, "contracted_amount"),
            Tile(2, 12, 6, 3, "lagging_project_count"),
            Tile(2, 18, 6, 3, "lagging_contracted_amount"),
            Tile(5, 0, 12, 7, "contracted_vs_accrued_by_level"),
            Tile(5, 12, 12, 7, "progress_distribution"),
            Tile(12, 0, 24, 8, "contracted_by_department"),
            Tile(20, 0, 24, 9, "lagging_projects"),
            Tile(29, 0, 24, 9, "contracted_above_cost"),
        ),
    ),
)

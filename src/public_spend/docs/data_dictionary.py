"""Render the data dictionary of the marts from dbt's manifest and catalog.

The manifest holds the descriptions written in the models' YAML files; the
catalog holds the column types of the built tables. Every mart column must be
described, otherwise rendering fails and names the gaps.

    cd dbt && dbt docs generate && cd ..
    python -m public_spend.docs.data_dictionary
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TARGET_DIR = REPO_ROOT / "dbt" / "target"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "data-dictionary.md"

SECTIONS = {
    "core": "Dimensions and facts",
    "analytics": "Analytical marts",
}


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    description: str
    is_key: bool


@dataclass(frozen=True)
class Model:
    name: str
    relation: str
    section: str
    description: str
    columns: tuple[Column, ...]


def _path_parts(path: str) -> list[str]:
    return re.split(r"[\\/]", path)


def unique_columns(manifest: dict[str, Any]) -> dict[str, set[str]]:
    """Columns with a `unique` test, per model unique_id."""
    keys: dict[str, set[str]] = {}
    for node in manifest["nodes"].values():
        if node.get("resource_type") != "test" or not node.get("column_name"):
            continue
        if node.get("test_metadata", {}).get("name") != "unique":
            continue
        keys.setdefault(node["attached_node"], set()).add(node["column_name"])
    return keys


def mart_models(manifest: dict[str, Any], catalog: dict[str, Any]) -> list[Model]:
    keys = unique_columns(manifest)
    models = []
    missing = []
    for unique_id, node in manifest["nodes"].items():
        if node.get("resource_type") != "model":
            continue
        parts = _path_parts(node["path"])
        if parts[0] != "marts" or unique_id not in catalog["nodes"]:
            continue
        declared = node["columns"]
        columns = []
        for name, column in catalog["nodes"][unique_id]["columns"].items():
            description = declared.get(name, {}).get("description", "").strip()
            if not description:
                missing.append(f"{node['name']}.{name}")
            columns.append(
                Column(name, column["type"], description, name in keys.get(unique_id, set()))
            )
        models.append(
            Model(
                name=node["name"],
                relation=f"{node['schema']}.{node['name']}",
                section=parts[1],
                description=node.get("description", "").strip(),
                columns=tuple(columns),
            )
        )
    if missing:
        raise ValueError("columns without a description: " + ", ".join(sorted(missing)))
    return sorted(models, key=lambda model: (model.section != "core", model.name))


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render(models: list[Model]) -> str:
    lines = [
        "# Data dictionary",
        "",
        "Columns of the `marts` schema, the layer read by Metabase and Power BI.",
        "Generated from the dbt manifest and catalog with",
        "`python -m public_spend.docs.data_dictionary`; edit the descriptions in",
        "`dbt/models/marts/**/*.yml` instead of this file. Key columns are in bold.",
        "",
    ]
    for section, title in SECTIONS.items():
        section_models = [model for model in models if model.section == section]
        if not section_models:
            continue
        lines += [f"## {title}", ""]
        for model in section_models:
            lines += [
                f"### {model.name}",
                "",
                f"`{model.relation}`. {_cell(model.description)}",
                "",
                "| Column | Type | Description |",
                "|--------|------|-------------|",
            ]
            for column in model.columns:
                name = f"**{column.name}**" if column.is_key else column.name
                lines.append(f"| {name} | {column.data_type} | {_cell(column.description)} |")
            lines.append("")
    return "\n".join(lines)


def build(target_dir: Path, output: Path) -> int:
    manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads((target_dir / "catalog.json").read_text(encoding="utf-8"))
    models = mart_models(manifest, catalog)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(models), encoding="utf-8", newline="\n")
    return len(models)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_TARGET_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = build(args.target_dir, args.output)
    print(f"wrote {args.output} ({count} models)")


if __name__ == "__main__":
    main()

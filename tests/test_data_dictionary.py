import json

import pytest

from public_spend.docs import data_dictionary as dd


def model_node(name, section, columns, path_sep="/"):
    return {
        "resource_type": "model",
        "name": name,
        "schema": "marts",
        "path": path_sep.join(["marts", section, f"{name}.sql"]),
        "description": f"Describes {name}.",
        "columns": {col: {"description": desc} for col, desc in columns.items()},
    }


def catalog_node(columns):
    return {"columns": {col: {"type": type_} for col, type_ in columns.items()}}


MANIFEST = {
    "nodes": {
        "model.p.fct_award": model_node(
            "fct_award", "core", {"award_key": "Surrogate key.", "amount": "Amount | in soles."}
        ),
        "model.p.mart_x": model_node("mart_x", "analytics", {"id": "The id."}, path_sep="\\"),
        "model.p.stg_x": model_node("stg_x", "oece", {}) | {"path": "staging/oece/stg_x.sql"},
        "test.p.unique_fct_award_award_key": {
            "resource_type": "test",
            "column_name": "award_key",
            "attached_node": "model.p.fct_award",
            "test_metadata": {"name": "unique"},
        },
    }
}
CATALOG = {
    "nodes": {
        "model.p.fct_award": catalog_node({"award_key": "text", "amount": "numeric"}),
        "model.p.mart_x": catalog_node({"id": "integer"}),
        "model.p.stg_x": catalog_node({"x": "text"}),
    }
}


def test_only_mart_models_are_selected_core_first():
    models = dd.mart_models(MANIFEST, CATALOG)
    assert [m.name for m in models] == ["fct_award", "mart_x"]
    assert [m.section for m in models] == ["core", "analytics"]


def test_columns_carry_type_description_and_key_flag():
    award = dd.mart_models(MANIFEST, CATALOG)[0]
    assert award.relation == "marts.fct_award"
    assert [(c.name, c.data_type, c.is_key) for c in award.columns] == [
        ("award_key", "text", True),
        ("amount", "numeric", False),
    ]


def test_missing_description_fails_with_the_column_name():
    catalog = json.loads(json.dumps(CATALOG))
    catalog["nodes"]["model.p.mart_x"]["columns"]["extra"] = {"type": "text"}
    with pytest.raises(ValueError, match=r"mart_x\.extra"):
        dd.mart_models(MANIFEST, catalog)


def test_render_escapes_pipes_and_bolds_keys():
    text = dd.render(dd.mart_models(MANIFEST, CATALOG))
    assert "## Dimensions and facts" in text
    assert "## Analytical marts" in text
    assert "| **award_key** | text | Surrogate key. |" in text
    assert "| amount | numeric | Amount \\| in soles. |" in text
    assert text.index("### fct_award") < text.index("### mart_x")


def test_build_writes_the_file(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "manifest.json").write_text(json.dumps(MANIFEST))
    (target / "catalog.json").write_text(json.dumps(CATALOG))
    output = tmp_path / "docs" / "data-dictionary.md"

    assert dd.build(target, output) == 2
    assert output.read_text(encoding="utf-8").startswith("# Data dictionary")

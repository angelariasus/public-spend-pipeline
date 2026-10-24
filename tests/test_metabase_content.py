import json
import re
from itertools import combinations

import pytest

from public_spend.metabase.content import DASHBOARDS, GRID_WIDTH, QUESTIONS, merge, percent, soles
from public_spend.metabase.provision import DEFAULT_QUESTIONS_DIR


def test_question_keys_and_names_are_unique():
    # Cards are matched by name on re-runs, so a repeated name would overwrite another card.
    assert len({q.key for q in QUESTIONS}) == len(QUESTIONS)
    assert len({q.name for q in QUESTIONS}) == len(QUESTIONS)


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q.key)
def test_question_sql_exists_and_reads_only_marts(question):
    sql = (DEFAULT_QUESTIONS_DIR / f"{question.key}.sql").read_text(encoding="utf-8")
    schemas = re.findall(r"\b(?:from|join)\s+(\w+)\.", sql)
    assert schemas
    assert set(schemas) == {"marts"}
    json.dumps(question.settings)


def test_every_sql_file_is_used():
    files = {path.stem for path in DEFAULT_QUESTIONS_DIR.glob("*.sql")}
    assert files == {q.key for q in QUESTIONS}


def test_every_question_is_on_a_dashboard():
    placed = {tile.question for d in DASHBOARDS for tile in d.tiles if tile.question}
    assert placed == {q.key for q in QUESTIONS}


@pytest.mark.parametrize("dashboard", DASHBOARDS, ids=lambda d: d.name)
def test_tiles_fit_the_grid_without_overlapping(dashboard):
    for tile in dashboard.tiles:
        assert (tile.question is None) != (tile.text is None)
        assert tile.col >= 0 and tile.col + tile.width <= GRID_WIDTH

    def cells(tile):
        return {
            (row, col)
            for row in range(tile.row, tile.row + tile.height)
            for col in range(tile.col, tile.col + tile.width)
        }

    for first, second in combinations(dashboard.tiles, 2):
        assert not cells(first) & cells(second), (first, second)


def test_merge_combines_column_settings():
    merged = merge(soles("amount"), percent("share"), {"graph.metrics": ["amount"]})
    assert merged["graph.metrics"] == ["amount"]
    assert merged["column_settings"] == {
        '["name", "amount"]': {"prefix": "S/ ", "decimals": 0},
        '["name", "share"]': {"number_style": "percent", "decimals": 1},
    }


def test_column_titles_merge_with_formatting():
    question = next(q for q in QUESTIONS if q.key == "awarded_amount")
    settings = question.visualization_settings()["column_settings"]
    assert settings['["name", "awarded_amount_pen"]'] == {
        "column_title": "Awarded (S/)",
        "prefix": "S/ ",
        "decimals": 0,
    }

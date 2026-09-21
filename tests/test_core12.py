from __future__ import annotations

import json
from pathlib import Path

import pytest

from chainshot.constants import to_cell
from chainshot.models import Direction, State, bitboard_from_cells
from chainshot.solver import solve


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "core12.json"


def load_core12() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["levels"]


def make_state(level: dict) -> State:
    cue = to_cell(*level["cue"])
    balls = bitboard_from_cells([to_cell(*coords) for coords in level["balls"]])
    return State(cue=cue, balls=balls)


@pytest.mark.parametrize("level", load_core12(), ids=lambda level: level["id"])
def test_core12_regression(level: dict) -> None:
    result = solve(make_state(level), max_depth=12, max_states=50_000)

    assert not result.exhausted
    assert result.solvable
    assert result.min_moves == level["expectedPar"]
    assert result.shortest_solution_count == level["expectedShortestSolutions"]

    expected_solution = tuple(Direction[name] for name in level["canonicalSolution"])
    assert expected_solution in result.sample_solutions

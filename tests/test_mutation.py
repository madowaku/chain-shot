from __future__ import annotations

import json
import random
from pathlib import Path

from chainshot.benchmark import evaluate_entry
from chainshot.constants import POCKET_CELLS, to_cell
from chainshot.models import State, bitboard_from_cells, cells_from_bitboard
from chainshot.mutation import (
    load_top_generated_parents,
    mutate_state,
    run_mutation_search,
)


def make_parent() -> State:
    return State(
        cue=to_cell(4, 6),
        balls=bitboard_from_cells(
            [
                to_cell(2, 6),
                to_cell(4, 5),
                to_cell(5, 0),
            ]
        ),
    )


def test_mutate_state_is_seeded_and_keeps_valid_ball_count() -> None:
    left_rng = random.Random(20260921)
    right_rng = random.Random(20260921)
    parent = make_parent()

    left = [mutate_state(parent, left_rng) for _ in range(50)]
    right = [mutate_state(parent, right_rng) for _ in range(50)]

    assert left == right

    for state, _ in left:
        balls = cells_from_bitboard(state.balls)
        assert 3 <= len(balls) <= 6
        assert state.cue not in POCKET_CELLS
        assert all(ball not in POCKET_CELLS for ball in balls)
        assert state.cue not in balls


def test_load_top_generated_parents_preserves_generated_rank_order(tmp_path: Path) -> None:
    path = tmp_path / "ranking.json"
    path.write_text(
        json.dumps(
            [
                {
                    "source": "CORE",
                    "id": "CORE-X",
                    "name": "CORE",
                    "cue": [5, 3],
                    "balls": [[3, 3]],
                },
                {
                    "source": "GENERATED",
                    "id": "GEN-A",
                    "name": "A",
                    "cue": [4, 6],
                    "balls": [[2, 6], [3, 6]],
                },
                {
                    "source": "GENERATED",
                    "id": "GEN-B",
                    "name": "B",
                    "cue": [1, 2],
                    "balls": [[2, 0], [3, 0], [5, 0]],
                },
            ]
        ),
        encoding="utf-8",
    )

    parents = load_top_generated_parents(path, top_n=2)

    assert [parent.entry_id for parent in parents] == ["GEN-A", "GEN-B"]


def test_mutation_search_keeps_only_parent_beaters() -> None:
    parent_state = State(
        cue=to_cell(1, 2),
        balls=bitboard_from_cells(
            [
                to_cell(2, 0),
                to_cell(3, 0),
                to_cell(5, 0),
            ]
        ),
    )
    parent = evaluate_entry(
        source="PARENT",
        entry_id="ZIPPER-PARENT",
        name="ZIPPER",
        state=parent_state,
    )

    run = run_mutation_search(
        parents=(parent,),
        per_parent=30,
        seed=1234,
    )

    assert len(run.parent_summaries) == 1
    assert run.parent_summaries[0].requested == 30
    assert run.parent_summaries[0].unique_children <= 30
    assert all(
        beater.child.scores.interestingness > beater.parent_score
        for beater in run.beaters
    )

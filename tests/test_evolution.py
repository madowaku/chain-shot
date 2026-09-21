from __future__ import annotations

import random
from pathlib import Path

from chainshot.benchmark import evaluate_entry
from chainshot.constants import POCKET_CELLS, to_cell
from chainshot.evolution import render_evolution_run, run_evolution_search, write_evolution_run
from chainshot.models import State, bitboard_from_cells, cells_from_bitboard
from chainshot.mutation import mutate_state_v2


def make_parent_state() -> State:
    return State(
        cue=to_cell(1, 2),
        balls=bitboard_from_cells(
            [
                to_cell(2, 0),
                to_cell(3, 0),
                to_cell(5, 0),
            ]
        ),
    )


def test_mutation_v2_is_seeded_and_valid() -> None:
    parent = make_parent_state()
    left_rng = random.Random(20260921)
    right_rng = random.Random(20260921)

    left = [mutate_state_v2(parent, left_rng) for _ in range(80)]
    right = [mutate_state_v2(parent, right_rng) for _ in range(80)]

    assert left == right

    operators = {operator for _, operator in left}
    assert operators <= {
        "cue_relocate",
        "ball_relocate",
        "ball_add_aligned",
        "ball_add_random",
        "ball_remove",
    }
    assert any(operator.startswith("ball_add") for operator in operators)

    for state, _ in left:
        balls = cells_from_bitboard(state.balls)
        assert 3 <= len(balls) <= 6
        assert state.cue not in POCKET_CELLS
        assert state.cue not in balls
        assert all(ball not in POCKET_CELLS for ball in balls)


def test_two_generation_evolution_is_reproducible(tmp_path: Path) -> None:
    root = evaluate_entry(
        source="PARENT",
        entry_id="ZIPPER-ROOT",
        name="ZIPPER",
        state=make_parent_state(),
    )

    kwargs = dict(
        roots=(root,),
        first_generation_per_parent=30,
        second_generation_per_parent=10,
        elites_per_root=1,
        seed=424242,
    )
    left = run_evolution_search(**kwargs)
    right = run_evolution_search(**kwargs)

    assert left.summary_dict() == right.summary_dict()
    assert [node.child.entry_id for node in left.beaters] == [
        node.child.entry_id for node in right.beaters
    ]
    assert all(node.improvement_from_parent > 0 for node in left.beaters)

    text = render_evolution_run(left)
    assert "MUTATION GENERATOR v0.2" in text
    assert "Generation 1" in text
    assert "Generation 2" in text

    write_evolution_run(tmp_path, left)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "all_beaters.json").exists()
    assert (tmp_path / "top_20.json").exists()
    assert (tmp_path / "elite.json").exists()
    assert (tmp_path / "ranking.txt").exists()
    assert (tmp_path / "lineage_review.txt").exists()

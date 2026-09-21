from __future__ import annotations

import random

from chainshot.generator import generate_candidates, generate_random_state
from chainshot.symmetry import canonical_key


def test_seeded_random_generation_is_reproducible() -> None:
    left_rng = random.Random(20260921)
    right_rng = random.Random(20260921)

    left = [generate_random_state(left_rng) for _ in range(20)]
    right = [generate_random_state(right_rng) for _ in range(20)]

    assert left == right


def test_forced_ball_count_is_respected() -> None:
    rng = random.Random(7)
    state = generate_random_state(rng, ball_count=6)

    assert state.balls.bit_count() == 6


def test_candidate_generation_is_reproducible_and_filtered() -> None:
    left, left_summary = generate_candidates(
        count=40,
        seed=12345,
        min_moves=4,
        max_moves=12,
        max_states=50_000,
        ball_count=3,
    )
    right, right_summary = generate_candidates(
        count=40,
        seed=12345,
        min_moves=4,
        max_moves=12,
        max_states=50_000,
        ball_count=3,
    )

    assert left_summary == right_summary
    assert [candidate.to_dict() for candidate in left] == [
        candidate.to_dict() for candidate in right
    ]

    keys = [canonical_key(candidate.state) for candidate in left]
    assert len(keys) == len(set(keys))

    for candidate in left:
        assert candidate.solve_result.solvable
        assert not candidate.solve_result.exhausted
        assert candidate.solve_result.min_moves is not None
        assert 4 <= candidate.solve_result.min_moves <= 12


def test_summary_accounts_for_every_requested_board() -> None:
    _, summary = generate_candidates(
        count=25,
        seed=999,
        min_moves=4,
        max_moves=12,
        ball_count=3,
    )

    accounted = (
        summary.duplicates
        + summary.exhausted
        + summary.unsolved_or_too_hard
        + summary.too_easy
        + summary.candidates
    )
    assert accounted == summary.requested
    assert summary.generated + summary.duplicates == summary.requested

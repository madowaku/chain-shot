from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .analyzer import LevelMetrics, analyze_level
from .constants import CELL_COUNT, POCKET_CELLS, to_coord
from .evaluator import ScoreBundle, score_level
from .models import State, bitboard_from_cells, cells_from_bitboard
from .solver import SolveResult, solve
from .symmetry import canonical_key


DEFAULT_BALL_COUNTS = (3, 4, 5, 6)
DEFAULT_BALL_WEIGHTS = (0.20, 0.30, 0.30, 0.20)


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    state: State
    solve_result: SolveResult
    metrics: LevelMetrics
    scores: ScoreBundle

    def to_dict(self) -> dict:
        cue_row, cue_col = to_coord(self.state.cue)
        balls = [list(to_coord(cell)) for cell in cells_from_bitboard(self.state.balls)]
        solution = (
            [direction.name for direction in self.solve_result.sample_solutions[0]]
            if self.solve_result.sample_solutions
            else []
        )
        analysis = {
            "minMoves": self.solve_result.min_moves,
            "solutionCount": self.solve_result.shortest_solution_count,
            "visitedStates": self.solve_result.visited_states,
            "expandedStates": self.solve_result.expanded_states,
        }
        analysis.update(self.metrics.to_dict())
        analysis.update(self.scores.to_dict())

        return {
            "id": self.candidate_id,
            "cue": [cue_row, cue_col],
            "balls": balls,
            "analysis": analysis,
            "solution": solution,
        }


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    seed: int
    requested: int
    generated: int
    duplicates: int
    exhausted: int
    unsolved_or_too_hard: int
    too_easy: int
    candidates: int
    unique_candidates: int
    par_distribution: dict[str, int]
    ball_count_distribution: dict[str, int]
    solution_count_distribution: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "requested": self.requested,
            "generated": self.generated,
            "duplicates": self.duplicates,
            "exhausted": self.exhausted,
            "unsolvedOrTooHard": self.unsolved_or_too_hard,
            "tooEasy": self.too_easy,
            "candidates": self.candidates,
            "uniqueCandidates": self.unique_candidates,
            "parDistribution": self.par_distribution,
            "ballCountDistribution": self.ball_count_distribution,
            "solutionCountDistribution": self.solution_count_distribution,
        }


def _distribution(values: list[int]) -> dict[str, int]:
    counts = Counter(values)
    return {str(key): counts[key] for key in sorted(counts)}


def generate_random_state(
    rng: random.Random,
    *,
    ball_count: int | None = None,
    ball_counts: tuple[int, ...] = DEFAULT_BALL_COUNTS,
    ball_weights: tuple[float, ...] = DEFAULT_BALL_WEIGHTS,
) -> State:
    if ball_count is None:
        ball_count = rng.choices(ball_counts, weights=ball_weights, k=1)[0]

    if ball_count < 1:
        raise ValueError("ball_count must be positive")

    playable_cells = [cell for cell in range(CELL_COUNT) if cell not in POCKET_CELLS]
    if ball_count + 1 > len(playable_cells):
        raise ValueError("too many balls for board")

    chosen = rng.sample(playable_cells, ball_count + 1)
    cue = chosen[0]
    balls = bitboard_from_cells(chosen[1:])
    return State(cue=cue, balls=balls)


def generate_candidates(
    *,
    count: int,
    seed: int,
    min_moves: int = 4,
    max_moves: int = 12,
    max_states: int = 50_000,
    ball_count: int | None = None,
) -> tuple[list[Candidate], GenerationSummary]:
    if count < 0:
        raise ValueError("count must be non-negative")
    if min_moves < 0 or max_moves < min_moves:
        raise ValueError("invalid move range")

    rng = random.Random(seed)
    seen: set[tuple[int, int]] = set()
    candidates: list[Candidate] = []

    duplicates = 0
    exhausted = 0
    unsolved_or_too_hard = 0
    too_easy = 0

    for index in range(1, count + 1):
        state = generate_random_state(rng, ball_count=ball_count)
        key = canonical_key(state)

        if key in seen:
            duplicates += 1
            continue
        seen.add(key)

        result = solve(state, max_depth=max_moves, max_states=max_states)

        if result.exhausted:
            exhausted += 1
            continue
        if not result.solvable or result.min_moves is None:
            unsolved_or_too_hard += 1
            continue
        if result.min_moves < min_moves:
            too_easy += 1
            continue

        candidates.append(
            Candidate(
                candidate_id=f"GEN-{index:06d}",
                state=state,
                solve_result=result,
                metrics=(metrics := analyze_level(state, result, max_states=max_states)),
                scores=score_level(result, metrics),
            )
        )

    par_values = [
        candidate.solve_result.min_moves
        for candidate in candidates
        if candidate.solve_result.min_moves is not None
    ]
    ball_counts = [candidate.state.balls.bit_count() for candidate in candidates]
    solution_counts = [
        candidate.solve_result.shortest_solution_count for candidate in candidates
    ]

    summary = GenerationSummary(
        seed=seed,
        requested=count,
        generated=len(seen),
        duplicates=duplicates,
        exhausted=exhausted,
        unsolved_or_too_hard=unsolved_or_too_hard,
        too_easy=too_easy,
        candidates=len(candidates),
        unique_candidates=sum(1 for count in solution_counts if count == 1),
        par_distribution=_distribution(par_values),
        ball_count_distribution=_distribution(ball_counts),
        solution_count_distribution=_distribution(solution_counts),
    )
    return candidates, summary

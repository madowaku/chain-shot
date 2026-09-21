from __future__ import annotations

import math
from dataclasses import dataclass

from .analyzer import LevelMetrics
from .solver import SolveResult


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _solution_uniqueness(solution_count: int) -> float:
    if solution_count <= 1:
        return 1.0
    if solution_count == 2:
        return 0.7
    if solution_count == 3:
        return 0.5
    if solution_count == 4:
        return 0.35
    return 0.15


def difficulty_score(result: SolveResult, metrics: LevelMetrics) -> float:
    if result.min_moves is None:
        return 0.0

    move_depth = _clamp01((result.min_moves - 4) / 8)
    search_complexity = _clamp01(math.log2(result.expanded_states + 1) / 9.0)

    if result.min_moves <= 1:
        change_ratio = 0.0
    else:
        change_ratio = _clamp01(metrics.direction_changes / (result.min_moves - 1))

    uniqueness = _solution_uniqueness(result.shortest_solution_count)

    score = 100.0 * (
        0.45 * move_depth
        + 0.35 * search_complexity
        + 0.10 * change_ratio
        + 0.10 * uniqueness
    )
    return round(score, 1)


def interestingness_score(result: SolveResult, metrics: LevelMetrics) -> float:
    built_chain = _clamp01(metrics.built_chain_gain / 3.0)
    setup = _clamp01(metrics.setup_shots / 2.0)
    temptation = _clamp01(metrics.temptation_count / 2.0)
    endgame = max(
        _clamp01(metrics.endgame_sinks / 3.0),
        _clamp01(metrics.endgame_sink_streak / 3.0),
    )
    transport = _clamp01(metrics.transport_distance / 6.0)
    cascade = _clamp01(metrics.max_cascade / 3.0)
    uniqueness = _solution_uniqueness(result.shortest_solution_count)

    cue_reposition = (
        1.0
        if 1.0 <= metrics.cue_repositions <= 2.0
        else 0.3
        if metrics.cue_repositions == 0
        else 0.5
        if metrics.cue_repositions < 4
        else 0.0
    )

    direction_diversity = _clamp01(metrics.direction_count / 4.0)
    search_complexity = _clamp01(math.log2(result.expanded_states + 1) / 9.0)

    weighted = (
        20 * built_chain
        + 15 * setup
        + 15 * temptation
        + 15 * endgame
        + 10 * transport
        + 10 * cascade
        + 8 * uniqueness
        + 5 * cue_reposition
        + 5 * direction_diversity
        + 7 * search_complexity
    )

    score = 100.0 * weighted / 110.0

    if result.shortest_solution_count >= 5:
        score -= 15.0
    if metrics.direction_count <= 1.0:
        score -= 10.0
    if (
        metrics.setup_shots == 0
        and metrics.built_chain_gain == 0
        and metrics.max_cascade <= 1
    ):
        score -= 25.0

    return round(max(0.0, min(100.0, score)), 1)


@dataclass(frozen=True, slots=True)
class ScoreBundle:
    difficulty: float
    interestingness: float

    def to_dict(self) -> dict:
        return {
            "difficultyScore": self.difficulty,
            "interestingnessScore": self.interestingness,
        }


def score_level(result: SolveResult, metrics: LevelMetrics) -> ScoreBundle:
    return ScoreBundle(
        difficulty=difficulty_score(result, metrics),
        interestingness=interestingness_score(result, metrics),
    )

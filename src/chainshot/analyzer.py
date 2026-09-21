from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .models import Direction, State
from .simulator import simulate_shot
from .solver import SolveResult, solve


ENDGAME_WINDOW = 3


@dataclass(frozen=True, slots=True)
class PathMetrics:
    sink_delay: int
    setup_shots: int
    cue_repositions: int
    transport_distance: int
    max_cascade: int
    avg_cascade: float
    initial_cascade_capacity: int
    max_cascade_capacity: int
    initial_chain_capacity: int
    max_chain_capacity: int
    built_chain_gain: int
    temptation_count: int
    direction_count: int
    direction_changes: int
    endgame_sinks: int
    endgame_sink_streak: int


@dataclass(frozen=True, slots=True)
class LevelMetrics:
    sink_delay: float
    setup_shots: float
    cue_repositions: float
    transport_distance: float
    max_cascade: int
    avg_cascade: float
    initial_cascade_capacity: int
    max_cascade_capacity: int
    initial_chain_capacity: int
    max_chain_capacity: int
    built_chain_gain: int
    temptation_count: int
    direction_count: float
    direction_changes: float
    endgame_sinks: float
    endgame_sink_streak: float

    def to_dict(self) -> dict:
        return {
            "sinkDelay": round(self.sink_delay, 3),
            "setupShots": round(self.setup_shots, 3),
            "cueRepositions": round(self.cue_repositions, 3),
            "transportDistance": round(self.transport_distance, 3),
            "maxCascade": self.max_cascade,
            "avgCascade": round(self.avg_cascade, 3),
            "initialCascadeCapacity": self.initial_cascade_capacity,
            "maxCascadeCapacity": self.max_cascade_capacity,
            "initialChainCapacity": self.initial_chain_capacity,
            "maxChainCapacity": self.max_chain_capacity,
            "builtChainGain": self.built_chain_gain,
            "temptationCount": self.temptation_count,
            "directionCount": round(self.direction_count, 3),
            "directionChanges": round(self.direction_changes, 3),
            "endgameSinks": round(self.endgame_sinks, 3),
            "endgameSinkStreak": round(self.endgame_sink_streak, 3),
        }


def true_chain_capacity_from_collisions(collisions: int) -> int:
    """Count only handoffs beyond the first cue-to-object collision as chain depth."""
    return max(0, collisions - 1)


def cascade_capacity(state: State) -> int:
    return max(
        (
            result.collision_count
            for direction in Direction
            if (result := simulate_shot(state, direction)).legal and result.changed
        ),
        default=0,
    )


def temptation_directions(
    state: State,
    optimal_remaining: int,
    *,
    max_states: int = 50_000,
    cache: dict[tuple[State, int], bool] | None = None,
) -> tuple[Direction, ...]:
    """Return immediate sinking actions that fail to preserve the optimal budget.

    If the current state is optimally solvable in R shots, a sinking action is
    tempting when its successor cannot finish within R-1 shots. This deliberately
    treats both true dead ends and merely longer routes as temptations.
    """
    if optimal_remaining <= 0:
        return ()

    local_cache = cache if cache is not None else {}
    temptations: list[Direction] = []

    for direction in Direction:
        shot = simulate_shot(state, direction)
        if (
            not shot.legal
            or not shot.changed
            or shot.next_state is None
            or shot.sunk_count <= 0
        ):
            continue

        budget = optimal_remaining - 1
        key = (shot.next_state, budget)

        preserves_optimal = local_cache.get(key)
        if preserves_optimal is None:
            if shot.next_state.balls == 0:
                preserves_optimal = budget >= 0
            elif budget <= 0:
                preserves_optimal = False
            else:
                followup = solve(
                    shot.next_state,
                    max_depth=budget,
                    max_states=max_states,
                    sample_limit=1,
                )
                preserves_optimal = (
                    followup.solvable
                    and not followup.exhausted
                    and followup.min_moves is not None
                    and followup.min_moves <= budget
                )
            local_cache[key] = preserves_optimal

        if not preserves_optimal:
            temptations.append(direction)

    return tuple(temptations)


def analyze_path(
    initial: State,
    solution: tuple[Direction, ...],
    *,
    max_states: int = 50_000,
) -> PathMetrics:
    state = initial
    capacities = [cascade_capacity(state)]
    temptation_cache: dict[tuple[State, int], bool] = {}
    temptation_pairs: set[tuple[State, Direction]] = set()

    sink_delay = 0
    first_sink_seen = False
    setup_shots = 0
    cue_repositions = 0
    transport_distance = 0
    cascades: list[int] = []
    sunk_per_shot: list[int] = []

    for index, direction in enumerate(solution):
        remaining = len(solution) - index
        for tempting_direction in temptation_directions(
            state,
            remaining,
            max_states=max_states,
            cache=temptation_cache,
        ):
            temptation_pairs.add((state, tempting_direction))

        result = simulate_shot(state, direction, trace=True)
        if not result.legal or not result.changed or result.next_state is None:
            raise ValueError("solution contains an illegal or no-op action")

        sunk_per_shot.append(result.sunk_count)
        cascades.append(result.collision_count)

        if not first_sink_seen:
            if result.sunk_count > 0:
                first_sink_seen = True
            else:
                sink_delay += 1

        if result.object_distance > 0 and result.sunk_count == 0:
            setup_shots += 1
            transport_distance += result.object_distance

        if (
            result.cue_distance > 0
            and result.object_distance == 0
            and result.sunk_count == 0
            and result.collision_count == 0
        ):
            cue_repositions += 1

        state = result.next_state
        capacities.append(cascade_capacity(state))

    direction_count = len(set(solution))
    direction_changes = sum(
        1 for left, right in zip(solution, solution[1:]) if left != right
    )

    endgame = sunk_per_shot[-ENDGAME_WINDOW:]
    endgame_sinks = sum(endgame)

    streak = 0
    for sunk in reversed(sunk_per_shot):
        if sunk <= 0:
            break
        streak += 1

    initial_capacity = capacities[0]
    max_capacity = max(capacities, default=initial_capacity)
    initial_chain_capacity = true_chain_capacity_from_collisions(initial_capacity)
    max_chain_capacity = true_chain_capacity_from_collisions(max_capacity)

    return PathMetrics(
        sink_delay=sink_delay,
        setup_shots=setup_shots,
        cue_repositions=cue_repositions,
        transport_distance=transport_distance,
        max_cascade=max(cascades, default=0),
        avg_cascade=fmean(cascades) if cascades else 0.0,
        initial_cascade_capacity=initial_capacity,
        max_cascade_capacity=max_capacity,
        initial_chain_capacity=initial_chain_capacity,
        max_chain_capacity=max_chain_capacity,
        built_chain_gain=max(0, max_chain_capacity - initial_chain_capacity),
        temptation_count=len(temptation_pairs),
        direction_count=direction_count,
        direction_changes=direction_changes,
        endgame_sinks=endgame_sinks,
        endgame_sink_streak=streak,
    )


def analyze_level(
    initial: State,
    solve_result: SolveResult,
    *,
    max_states: int = 50_000,
) -> LevelMetrics:
    if not solve_result.solvable or not solve_result.sample_solutions:
        raise ValueError("level must have at least one sampled solution")

    paths = [
        analyze_path(initial, solution, max_states=max_states)
        for solution in solve_result.sample_solutions
    ]

    return LevelMetrics(
        sink_delay=fmean(path.sink_delay for path in paths),
        setup_shots=fmean(path.setup_shots for path in paths),
        cue_repositions=fmean(path.cue_repositions for path in paths),
        transport_distance=fmean(path.transport_distance for path in paths),
        max_cascade=max(path.max_cascade for path in paths),
        avg_cascade=fmean(path.avg_cascade for path in paths),
        initial_cascade_capacity=paths[0].initial_cascade_capacity,
        max_cascade_capacity=max(path.max_cascade_capacity for path in paths),
        initial_chain_capacity=paths[0].initial_chain_capacity,
        max_chain_capacity=max(path.max_chain_capacity for path in paths),
        built_chain_gain=max(path.built_chain_gain for path in paths),
        temptation_count=max(path.temptation_count for path in paths),
        direction_count=fmean(path.direction_count for path in paths),
        direction_changes=fmean(path.direction_changes for path in paths),
        endgame_sinks=fmean(path.endgame_sinks for path in paths),
        endgame_sink_streak=fmean(path.endgame_sink_streak for path in paths),
    )

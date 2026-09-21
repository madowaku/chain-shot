from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .models import Direction, State
from .simulator import simulate_shot
from .solver import SolveResult


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
    built_chain_gain: int
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
    built_chain_gain: int
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
            "builtChainGain": self.built_chain_gain,
            "directionCount": round(self.direction_count, 3),
            "directionChanges": round(self.direction_changes, 3),
            "endgameSinks": round(self.endgame_sinks, 3),
            "endgameSinkStreak": round(self.endgame_sink_streak, 3),
        }


def cascade_capacity(state: State) -> int:
    return max(
        (
            result.collision_count
            for direction in Direction
            if (result := simulate_shot(state, direction)).legal and result.changed
        ),
        default=0,
    )


def analyze_path(initial: State, solution: tuple[Direction, ...]) -> PathMetrics:
    state = initial
    capacities = [cascade_capacity(state)]

    sink_delay = 0
    first_sink_seen = False
    setup_shots = 0
    cue_repositions = 0
    transport_distance = 0
    cascades: list[int] = []
    sunk_per_shot: list[int] = []

    for direction in solution:
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

    return PathMetrics(
        sink_delay=sink_delay,
        setup_shots=setup_shots,
        cue_repositions=cue_repositions,
        transport_distance=transport_distance,
        max_cascade=max(cascades, default=0),
        avg_cascade=fmean(cascades) if cascades else 0.0,
        initial_cascade_capacity=initial_capacity,
        max_cascade_capacity=max_capacity,
        built_chain_gain=max(0, max_capacity - initial_capacity),
        direction_count=direction_count,
        direction_changes=direction_changes,
        endgame_sinks=endgame_sinks,
        endgame_sink_streak=streak,
    )


def analyze_level(initial: State, solve_result: SolveResult) -> LevelMetrics:
    if not solve_result.solvable or not solve_result.sample_solutions:
        raise ValueError("level must have at least one sampled solution")

    paths = [analyze_path(initial, solution) for solution in solve_result.sample_solutions]

    return LevelMetrics(
        sink_delay=fmean(path.sink_delay for path in paths),
        setup_shots=fmean(path.setup_shots for path in paths),
        cue_repositions=fmean(path.cue_repositions for path in paths),
        transport_distance=fmean(path.transport_distance for path in paths),
        max_cascade=max(path.max_cascade for path in paths),
        avg_cascade=fmean(path.avg_cascade for path in paths),
        initial_cascade_capacity=paths[0].initial_cascade_capacity,
        max_cascade_capacity=max(path.max_cascade_capacity for path in paths),
        built_chain_gain=max(path.built_chain_gain for path in paths),
        direction_count=fmean(path.direction_count for path in paths),
        direction_changes=fmean(path.direction_changes for path in paths),
        endgame_sinks=fmean(path.endgame_sinks for path in paths),
        endgame_sink_streak=fmean(path.endgame_sink_streak for path in paths),
    )

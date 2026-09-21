from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .models import Direction, State
from .simulator import simulate_shot


@dataclass(frozen=True, slots=True)
class SolveResult:
    solvable: bool
    min_moves: int | None
    shortest_solution_count: int
    visited_states: int
    expanded_states: int
    sample_solutions: tuple[tuple[Direction, ...], ...]
    exhausted: bool


def available_actions(state: State) -> tuple[tuple[Direction, State], ...]:
    successors: list[tuple[Direction, State]] = []
    for direction in Direction:
        result = simulate_shot(state, direction)
        if result.legal and result.changed and result.next_state is not None:
            successors.append((direction, result.next_state))
    return tuple(successors)


def solve(
    initial: State,
    *,
    max_depth: int = 12,
    max_states: int = 50_000,
    sample_limit: int = 16,
) -> SolveResult:
    """Solve a board exactly up to max_depth using breadth-first search."""

    if initial.balls == 0:
        return SolveResult(True, 0, 1, 1, 0, ((),), False)

    distance: dict[State, int] = {initial: 0}
    ways: dict[State, int] = {initial: 1}
    samples: dict[State, list[tuple[Direction, ...]]] = {initial: [()]}
    queue: deque[State] = deque([initial])

    expanded_states = 0
    goal_depth: int | None = None
    exhausted = False

    while queue:
        state = queue.popleft()
        depth = distance[state]

        if goal_depth is not None and depth >= goal_depth:
            break
        if depth >= max_depth:
            continue

        expanded_states += 1

        for action, next_state in available_actions(state):
            next_depth = depth + 1
            if goal_depth is not None and next_depth > goal_depth:
                continue

            derived_samples = [path + (action,) for path in samples[state]]

            if next_state not in distance:
                if len(distance) >= max_states:
                    exhausted = True
                    queue.clear()
                    break

                distance[next_state] = next_depth
                ways[next_state] = ways[state]
                samples[next_state] = derived_samples[:sample_limit]
                queue.append(next_state)
            elif distance[next_state] == next_depth:
                ways[next_state] += ways[state]
                if len(samples[next_state]) < sample_limit:
                    remaining = sample_limit - len(samples[next_state])
                    samples[next_state].extend(derived_samples[:remaining])

            if next_state.balls == 0:
                if goal_depth is None:
                    goal_depth = next_depth

        if exhausted:
            break

    if goal_depth is None:
        return SolveResult(
            solvable=False,
            min_moves=None,
            shortest_solution_count=0,
            visited_states=len(distance),
            expanded_states=expanded_states,
            sample_solutions=(),
            exhausted=exhausted,
        )

    goal_states = [
        state
        for state, depth in distance.items()
        if depth == goal_depth and state.balls == 0
    ]
    solution_count = sum(ways[state] for state in goal_states)

    solution_samples: list[tuple[Direction, ...]] = []
    for state in goal_states:
        for path in samples[state]:
            solution_samples.append(path)
            if len(solution_samples) >= sample_limit:
                break
        if len(solution_samples) >= sample_limit:
            break

    return SolveResult(
        solvable=True,
        min_moves=goal_depth,
        shortest_solution_count=solution_count,
        visited_states=len(distance),
        expanded_states=expanded_states,
        sample_solutions=tuple(solution_samples),
        exhausted=exhausted,
    )

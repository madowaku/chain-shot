from chainshot.analyzer import LevelMetrics
from chainshot.evaluator import difficulty_score, interestingness_score
from chainshot.models import Direction
from chainshot.solver import SolveResult


def result(
    *,
    moves: int,
    solutions: int = 1,
    expanded: int = 64,
) -> SolveResult:
    return SolveResult(
        solvable=True,
        min_moves=moves,
        shortest_solution_count=solutions,
        visited_states=expanded + 1,
        expanded_states=expanded,
        sample_solutions=((Direction.UP,) * moves,),
        exhausted=False,
    )


def metrics(**overrides) -> LevelMetrics:
    values = dict(
        sink_delay=1.0,
        setup_shots=1.0,
        cue_repositions=1.0,
        transport_distance=3.0,
        max_cascade=2,
        avg_cascade=1.0,
        initial_cascade_capacity=1,
        max_cascade_capacity=2,
        initial_chain_capacity=0,
        max_chain_capacity=1,
        built_chain_gain=1,
        temptation_count=1,
        direction_count=3.0,
        direction_changes=4.0,
        endgame_sinks=2.0,
        endgame_sink_streak=2.0,
    )
    values.update(overrides)
    return LevelMetrics(**values)


def test_difficulty_rises_with_deeper_search() -> None:
    easy = difficulty_score(result(moves=4, expanded=8), metrics(direction_changes=1.0))
    hard = difficulty_score(result(moves=10, expanded=256), metrics(direction_changes=7.0))

    assert hard > easy


def test_chain_shot_structure_scores_above_flat_level() -> None:
    strong = interestingness_score(
        result(moves=8, expanded=128),
        metrics(
            setup_shots=2.0,
            transport_distance=6.0,
            max_cascade=3,
            max_chain_capacity=2,
            built_chain_gain=2,
            temptation_count=2,
            endgame_sinks=3.0,
            endgame_sink_streak=3.0,
            direction_count=4.0,
        ),
    )
    flat = interestingness_score(
        result(moves=8, expanded=128),
        metrics(
            setup_shots=0.0,
            cue_repositions=0.0,
            transport_distance=0.0,
            max_cascade=1,
            avg_cascade=0.5,
            initial_cascade_capacity=1,
            max_cascade_capacity=1,
            initial_chain_capacity=0,
            max_chain_capacity=0,
            built_chain_gain=0,
            temptation_count=0,
            direction_count=1.0,
            direction_changes=0.0,
            endgame_sinks=1.0,
            endgame_sink_streak=1.0,
        ),
    )

    assert strong > flat
    assert 0.0 <= flat <= 100.0
    assert 0.0 <= strong <= 100.0

from chainshot.analyzer import analyze_path, temptation_directions, true_chain_capacity_from_collisions
from chainshot.constants import to_cell
from chainshot.models import Direction, State, bitboard_from_cells


def make_state(cue: tuple[int, int], balls: list[tuple[int, int]]) -> State:
    return State(
        cue=to_cell(*cue),
        balls=bitboard_from_cells([to_cell(*ball) for ball in balls]),
    )


def test_zipper_metrics_capture_built_chain_and_payoff() -> None:
    initial = make_state(
        (1, 2),
        [(2, 0), (3, 0), (5, 0)],
    )
    solution = (
        Direction.LEFT,
        Direction.DOWN,
        Direction.DOWN,
        Direction.DOWN,
    )

    metrics = analyze_path(initial, solution)

    assert metrics.sink_delay == 1
    assert metrics.cue_repositions == 1
    assert metrics.setup_shots == 0
    assert metrics.initial_cascade_capacity == 0
    assert metrics.max_cascade_capacity == 3
    assert metrics.initial_chain_capacity == 0
    assert metrics.max_chain_capacity == 2
    assert metrics.built_chain_gain == 2
    assert metrics.max_cascade == 3
    assert metrics.endgame_sinks == 3
    assert metrics.endgame_sink_streak == 3


def test_not_yet_metrics_capture_setup_transport() -> None:
    initial = make_state(
        (4, 3),
        [(1, 3), (2, 3), (4, 4)],
    )
    solution = (
        Direction.RIGHT,
        Direction.UP,
        Direction.UP,
        Direction.RIGHT,
        Direction.DOWN,
    )

    metrics = analyze_path(initial, solution)

    assert metrics.sink_delay == 1
    assert metrics.setup_shots == 1
    assert metrics.cue_repositions == 1
    assert metrics.transport_distance == 2
    assert metrics.max_cascade == 2
    assert metrics.direction_count == 3
    assert metrics.direction_changes == 3


def test_dont_sink_yet_detects_immediate_sink_as_temptation() -> None:
    initial = make_state(
        (4, 6),
        [(2, 6), (4, 5)],
    )

    assert temptation_directions(initial, 4) == (Direction.UP,)


def test_true_chain_capacity_starts_at_second_collision() -> None:
    assert true_chain_capacity_from_collisions(0) == 0
    assert true_chain_capacity_from_collisions(1) == 0
    assert true_chain_capacity_from_collisions(2) == 1
    assert true_chain_capacity_from_collisions(3) == 2

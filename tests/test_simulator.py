from chainshot.constants import to_cell
from chainshot.models import Direction, State, bitboard_from_cells, cells_from_bitboard
from chainshot.simulator import simulate_shot


def state(cue: tuple[int, int], balls: list[tuple[int, int]]) -> State:
    return State(
        cue=to_cell(*cue),
        balls=bitboard_from_cells([to_cell(*ball) for ball in balls]),
    )


def test_cue_moves_to_rail_when_lane_is_empty() -> None:
    initial = state((3, 3), [])
    result = simulate_shot(initial, Direction.RIGHT)

    assert result.legal
    assert result.changed
    assert result.next_state is not None
    assert result.next_state.cue == to_cell(3, 6)
    assert result.cue_distance == 3


def test_cue_entering_pocket_is_illegal() -> None:
    initial = state((1, 3), [])
    result = simulate_shot(initial, Direction.UP)

    assert not result.legal
    assert not result.changed
    assert result.next_state is None


def test_object_ball_sinks_after_collision() -> None:
    initial = state((2, 3), [(1, 3)])
    result = simulate_shot(initial, Direction.UP)

    assert result.legal
    assert result.changed
    assert result.next_state is not None
    assert result.next_state.balls == 0
    assert result.sunk_count == 1
    assert result.collision_count == 1
    assert result.object_distance == 1


def test_motion_transfers_through_multiple_balls() -> None:
    initial = state((3, 0), [(3, 2), (3, 4)])
    result = simulate_shot(initial, Direction.RIGHT)

    assert result.legal
    assert result.next_state is not None
    assert result.collision_count == 2
    assert result.next_state.cue == to_cell(3, 1)
    assert cells_from_bitboard(result.next_state.balls) == (to_cell(3, 3), to_cell(3, 6))

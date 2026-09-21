from chainshot.constants import to_cell
from chainshot.models import Direction, State, bitboard_from_cells
from chainshot.solver import solve


def state(cue: tuple[int, int], balls: list[tuple[int, int]]) -> State:
    return State(
        cue=to_cell(*cue),
        balls=bitboard_from_cells([to_cell(*ball) for ball in balls]),
    )


def test_already_solved_board_is_zero_moves() -> None:
    result = solve(state((3, 3), []))

    assert result.solvable
    assert result.min_moves == 0
    assert result.shortest_solution_count == 1
    assert result.sample_solutions == ((),)


def test_single_ball_has_one_move_solution() -> None:
    result = solve(state((2, 3), [(1, 3)]))

    assert result.solvable
    assert result.min_moves == 1
    assert result.shortest_solution_count == 1
    assert result.sample_solutions[0] == (Direction.UP,)


def test_solver_counts_two_shortest_action_sequences() -> None:
    initial = state((3, 3), [(1, 3), (5, 3)])
    result = solve(initial)

    assert result.solvable
    assert result.min_moves == 2
    assert result.shortest_solution_count == 2
    assert set(result.sample_solutions) == {
        (Direction.UP, Direction.DOWN),
        (Direction.DOWN, Direction.UP),
    }

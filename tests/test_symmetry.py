from chainshot.constants import to_cell
from chainshot.models import State, bitboard_from_cells
from chainshot.symmetry import Symmetry, canonical_key, transform_state


def make_state() -> State:
    return State(
        cue=to_cell(1, 2),
        balls=bitboard_from_cells(
            [
                to_cell(2, 5),
                to_cell(4, 1),
                to_cell(5, 4),
            ]
        ),
    )


def test_all_valid_symmetries_share_canonical_key() -> None:
    initial = make_state()
    expected = canonical_key(initial)

    for symmetry in Symmetry:
        assert canonical_key(transform_state(initial, symmetry)) == expected


def test_rotate_180_is_involution() -> None:
    initial = make_state()
    rotated = transform_state(initial, Symmetry.ROTATE_180)

    assert transform_state(rotated, Symmetry.ROTATE_180) == initial

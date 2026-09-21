from __future__ import annotations

from enum import IntEnum

from .constants import BOARD_SIZE
from .models import State, add_ball, cells_from_bitboard


class Symmetry(IntEnum):
    IDENTITY = 0
    FLIP_VERTICAL = 1
    FLIP_HORIZONTAL = 2
    ROTATE_180 = 3


def transform_cell(cell: int, symmetry: Symmetry) -> int:
    row, col = divmod(cell, BOARD_SIZE)

    if symmetry is Symmetry.IDENTITY:
        new_row, new_col = row, col
    elif symmetry is Symmetry.FLIP_VERTICAL:
        new_row, new_col = row, BOARD_SIZE - 1 - col
    elif symmetry is Symmetry.FLIP_HORIZONTAL:
        new_row, new_col = BOARD_SIZE - 1 - row, col
    elif symmetry is Symmetry.ROTATE_180:
        new_row, new_col = BOARD_SIZE - 1 - row, BOARD_SIZE - 1 - col
    else:
        raise ValueError(f"unsupported symmetry: {symmetry}")

    return new_row * BOARD_SIZE + new_col


def transform_state(state: State, symmetry: Symmetry) -> State:
    balls = 0
    for cell in cells_from_bitboard(state.balls):
        balls = add_ball(balls, transform_cell(cell, symmetry))

    return State(
        cue=transform_cell(state.cue, symmetry),
        balls=balls,
    )


def canonical_key(state: State) -> tuple[int, int]:
    """Return the lexicographically smallest cue/bitboard pair over valid table symmetries."""
    return min(
        (transformed.cue, transformed.balls)
        for transformed in (transform_state(state, symmetry) for symmetry in Symmetry)
    )

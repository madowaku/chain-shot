from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .constants import BOARD_SIZE, CELL_COUNT, POCKET_CELLS, to_coord


class Direction(IntEnum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3


DIRECTION_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.UP: (-1, 0),
    Direction.RIGHT: (0, 1),
    Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1),
}


@dataclass(frozen=True, slots=True)
class State:
    cue: int
    balls: int

    def __post_init__(self) -> None:
        if not (0 <= self.cue < CELL_COUNT):
            raise ValueError(f"cue cell out of range: {self.cue}")
        if self.cue in POCKET_CELLS:
            raise ValueError("cue cannot occupy a pocket")
        if self.balls < 0 or self.balls >= (1 << CELL_COUNT):
            raise ValueError("balls bitboard must fit in 49 bits")
        if has_ball(self.balls, self.cue):
            raise ValueError("cue and object ball cannot share a cell")
        if any(has_ball(self.balls, pocket) for pocket in POCKET_CELLS):
            raise ValueError("object ball cannot occupy a pocket")


@dataclass(frozen=True, slots=True)
class MotionSegment:
    mover: str
    start: int
    end: int
    distance: int
    outcome: str


@dataclass(frozen=True, slots=True)
class ShotTrace:
    segments: tuple[MotionSegment, ...]
    sunk_count: int
    collision_count: int


@dataclass(frozen=True, slots=True)
class ShotResult:
    legal: bool
    changed: bool
    next_state: State | None
    sunk_count: int = 0
    collision_count: int = 0
    cue_distance: int = 0
    object_distance: int = 0
    trace: ShotTrace | None = None


def has_ball(bitboard: int, cell: int) -> bool:
    return bool(bitboard & (1 << cell))


def add_ball(bitboard: int, cell: int) -> int:
    return bitboard | (1 << cell)


def remove_ball(bitboard: int, cell: int) -> int:
    return bitboard & ~(1 << cell)


def bitboard_from_cells(cells: list[int] | tuple[int, ...] | set[int]) -> int:
    bitboard = 0
    for cell in cells:
        if not (0 <= cell < CELL_COUNT):
            raise ValueError(f"ball cell out of range: {cell}")
        bitboard = add_ball(bitboard, cell)
    return bitboard


def cells_from_bitboard(bitboard: int) -> tuple[int, ...]:
    return tuple(cell for cell in range(CELL_COUNT) if has_ball(bitboard, cell))


def step_cell(cell: int, direction: Direction) -> int | None:
    row, col = to_coord(cell)
    dr, dc = DIRECTION_DELTAS[direction]
    row += dr
    col += dc
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        return None
    return row * BOARD_SIZE + col

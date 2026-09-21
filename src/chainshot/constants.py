BOARD_SIZE = 7
CELL_COUNT = BOARD_SIZE * BOARD_SIZE

POCKET_COORDS = frozenset({
    (0, 0),
    (0, 3),
    (0, 6),
    (6, 0),
    (6, 3),
    (6, 6),
})

POCKET_CELLS = frozenset(row * BOARD_SIZE + col for row, col in POCKET_COORDS)


def to_cell(row: int, col: int) -> int:
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        raise ValueError(f"coordinate out of range: {(row, col)}")
    return row * BOARD_SIZE + col


def to_coord(cell: int) -> tuple[int, int]:
    if not (0 <= cell < CELL_COUNT):
        raise ValueError(f"cell out of range: {cell}")
    return divmod(cell, BOARD_SIZE)

from chainshot.constants import to_cell
from chainshot.models import State, bitboard_from_cells
from chainshot.review import render_board, render_top_dicts


def test_render_board_uses_fixed_width_ascii_symbols() -> None:
    state = State(
        cue=to_cell(1, 1),
        balls=bitboard_from_cells([to_cell(2, 3), to_cell(5, 6)]),
    )

    assert render_board(state) == "\n".join(
        [
            "O . . O . . O",
            ". W . . . . .",
            ". . . o . . .",
            ". . . . . . .",
            ". . . . . . .",
            ". . . . . . o",
            "O . . O . . O",
        ]
    )


def test_render_top_dicts_includes_metrics_board_and_solution() -> None:
    item = {
        "id": "GEN-000001",
        "cue": [1, 1],
        "balls": [[2, 3]],
        "analysis": {
            "interestingnessScore": 77.6,
            "difficultyScore": 90.8,
            "minMoves": 4,
            "solutionCount": 1,
            "temptationCount": 2,
            "builtChainGain": 1,
            "setupShots": 1.0,
            "transportDistance": 3.0,
            "maxCascade": 2,
            "endgameSinkStreak": 2.0,
        },
        "solution": ["RIGHT", "DOWN", "LEFT", "UP"],
    }

    text = render_top_dicts([item])

    assert "#01 GEN-000001" in text
    assert "I=77.6" in text
    assert "T=2" in text
    assert "BC=+1" in text
    assert ". W . . . . ." in text
    assert "Solution: RIGHT DOWN LEFT UP" in text

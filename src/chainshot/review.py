from __future__ import annotations

from typing import Iterable

from .constants import BOARD_SIZE, POCKET_CELLS
from .generator import Candidate
from .models import State, has_ball


def render_board(state: State) -> str:
    rows: list[str] = []
    for row in range(BOARD_SIZE):
        cells: list[str] = []
        for col in range(BOARD_SIZE):
            cell = row * BOARD_SIZE + col
            if cell == state.cue:
                symbol = "W"
            elif has_ball(state.balls, cell):
                symbol = "o"
            elif cell in POCKET_CELLS:
                symbol = "O"
            else:
                symbol = "."
            cells.append(symbol)
        rows.append(" ".join(cells))
    return "\n".join(rows)


def render_candidate(candidate: Candidate, rank: int) -> str:
    result = candidate.solve_result
    metrics = candidate.metrics
    scores = candidate.scores
    solution = " ".join(direction.name for direction in result.sample_solutions[0])

    return "\n".join(
        [
            f"#{rank:02d} {candidate.candidate_id}",
            (
                f"I={scores.interestingness:.1f}  "
                f"D={scores.difficulty:.1f}  "
                f"PAR={result.min_moves}  "
                f"SOL={result.shortest_solution_count}  "
                f"T={metrics.temptation_count}  "
                f"BC=+{metrics.built_chain_gain}"
            ),
            (
                f"Setup={metrics.setup_shots:.1f}  "
                f"Transport={metrics.transport_distance:.1f}  "
                f"Cascade={metrics.max_cascade}  "
                f"EndStreak={metrics.endgame_sink_streak:.1f}"
            ),
            "",
            render_board(candidate.state),
            "",
            f"Solution: {solution}",
        ]
    )


def render_top_candidates(candidates: Iterable[Candidate]) -> str:
    blocks = [render_candidate(candidate, rank) for rank, candidate in enumerate(candidates, 1)]
    header = "\n".join(
        [
            "CHAIN SHOT TOP CANDIDATES",
            "Legend: W=cue  o=object  O=pocket  .=empty",
            "=" * 44,
            "",
        ]
    )
    return header + ("\n\n" + "-" * 44 + "\n\n").join(blocks) + "\n"


def render_candidate_dict(data: dict, rank: int) -> str:
    analysis = data["analysis"]
    board = _render_board_dict(data["cue"], data["balls"])
    solution = " ".join(data.get("solution", []))

    return "\n".join(
        [
            f"#{rank:02d} {data['id']}",
            (
                f"I={analysis['interestingnessScore']:.1f}  "
                f"D={analysis['difficultyScore']:.1f}  "
                f"PAR={analysis['minMoves']}  "
                f"SOL={analysis['solutionCount']}  "
                f"T={analysis['temptationCount']}  "
                f"BC=+{analysis['builtChainGain']}"
            ),
            (
                f"Setup={analysis['setupShots']:.1f}  "
                f"Transport={analysis['transportDistance']:.1f}  "
                f"Cascade={analysis['maxCascade']}  "
                f"EndStreak={analysis['endgameSinkStreak']:.1f}"
            ),
            "",
            board,
            "",
            f"Solution: {solution}",
        ]
    )


def render_top_dicts(items: list[dict], *, limit: int = 20) -> str:
    selected = items[:limit]
    blocks = [render_candidate_dict(item, rank) for rank, item in enumerate(selected, 1)]
    header = "\n".join(
        [
            "CHAIN SHOT TOP CANDIDATES",
            "Legend: W=cue  o=object  O=pocket  .=empty",
            "=" * 44,
            "",
        ]
    )
    return header + ("\n\n" + "-" * 44 + "\n\n").join(blocks) + "\n"


def _render_board_dict(cue: list[int], balls: list[list[int]]) -> str:
    cue_coord = tuple(cue)
    ball_coords = {tuple(ball) for ball in balls}
    rows: list[str] = []

    for row in range(BOARD_SIZE):
        cells: list[str] = []
        for col in range(BOARD_SIZE):
            coord = (row, col)
            cell = row * BOARD_SIZE + col
            if coord == cue_coord:
                symbol = "W"
            elif coord in ball_coords:
                symbol = "o"
            elif cell in POCKET_CELLS:
                symbol = "O"
            else:
                symbol = "."
            cells.append(symbol)
        rows.append(" ".join(cells))
    return "\n".join(rows)

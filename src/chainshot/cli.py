from __future__ import annotations

import argparse
import json
from pathlib import Path

from .constants import to_cell
from .models import State, bitboard_from_cells
from .solver import solve


def _state_from_json(path: Path) -> State:
    data = json.loads(path.read_text(encoding="utf-8"))
    cue_row, cue_col = data["cue"]
    ball_cells = [to_cell(row, col) for row, col in data["balls"]]
    return State(
        cue=to_cell(cue_row, cue_col),
        balls=bitboard_from_cells(ball_cells),
    )


def _cmd_solve(path: Path, max_depth: int, max_states: int) -> int:
    state = _state_from_json(path)
    result = solve(state, max_depth=max_depth, max_states=max_states)

    print("CHAIN SHOT SOLVER")
    print(f"Solved: {'YES' if result.solvable else 'NO'}")
    print(f"Minimum moves: {result.min_moves}")
    print(f"Shortest solutions: {result.shortest_solution_count}")
    print(f"Visited states: {result.visited_states}")
    print(f"Expanded states: {result.expanded_states}")
    print(f"Exhausted: {'YES' if result.exhausted else 'NO'}")

    if result.sample_solutions:
        print("Solution:")
        for direction in result.sample_solutions[0]:
            print(direction.name)
    return 0 if result.solvable else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chainshot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve a JSON level with BFS")
    solve_parser.add_argument("path", type=Path)
    solve_parser.add_argument("--max-depth", type=int, default=12)
    solve_parser.add_argument("--max-states", type=int, default=50_000)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "solve":
        return _cmd_solve(args.path, args.max_depth, args.max_states)
    parser.error("unknown command")
    return 2

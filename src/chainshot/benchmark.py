from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .analyzer import LevelMetrics, analyze_level
from .constants import to_cell, to_coord
from .evaluator import ScoreBundle, score_level
from .models import State, bitboard_from_cells, cells_from_bitboard
from .solver import SolveResult, solve


@dataclass(frozen=True, slots=True)
class BenchmarkEntry:
    source: str
    entry_id: str
    name: str
    state: State
    result: SolveResult
    metrics: LevelMetrics
    scores: ScoreBundle

    def to_dict(self) -> dict:
        cue = list(to_coord(self.state.cue))
        balls = [list(to_coord(cell)) for cell in cells_from_bitboard(self.state.balls)]
        solution = (
            [direction.name for direction in self.result.sample_solutions[0]]
            if self.result.sample_solutions
            else []
        )
        analysis = {
            "minMoves": self.result.min_moves,
            "solutionCount": self.result.shortest_solution_count,
            "visitedStates": self.result.visited_states,
            "expandedStates": self.result.expanded_states,
        }
        analysis.update(self.metrics.to_dict())
        analysis.update(self.scores.to_dict())
        return {
            "source": self.source,
            "id": self.entry_id,
            "name": self.name,
            "cue": cue,
            "balls": balls,
            "analysis": analysis,
            "solution": solution,
        }


def state_from_coords(cue: list[int], balls: list[list[int]]) -> State:
    return State(
        cue=to_cell(*cue),
        balls=bitboard_from_cells([to_cell(*ball) for ball in balls]),
    )


def evaluate_entry(
    *,
    source: str,
    entry_id: str,
    name: str,
    state: State,
    max_depth: int = 12,
    max_states: int = 50_000,
) -> BenchmarkEntry:
    result = solve(
        state,
        max_depth=max_depth,
        max_states=max_states,
        sample_limit=16,
    )
    if not result.solvable or result.min_moves is None or result.exhausted:
        raise ValueError(f"benchmark level is not fully solved: {entry_id}")

    metrics = analyze_level(state, result, max_states=max_states)
    scores = score_level(result, metrics)
    return BenchmarkEntry(
        source=source,
        entry_id=entry_id,
        name=name,
        state=state,
        result=result,
        metrics=metrics,
        scores=scores,
    )


def benchmark_core_and_generated(
    *,
    core_path: Path,
    generated_path: Path,
    max_depth: int = 12,
    max_states: int = 50_000,
) -> list[BenchmarkEntry]:
    core_data = json.loads(core_path.read_text(encoding="utf-8"))
    generated_data = json.loads(generated_path.read_text(encoding="utf-8"))

    entries: list[BenchmarkEntry] = []

    for level in core_data["levels"]:
        entries.append(
            evaluate_entry(
                source="CORE",
                entry_id=level["id"],
                name=level["name"],
                state=state_from_coords(level["cue"], level["balls"]),
                max_depth=max_depth,
                max_states=max_states,
            )
        )

    for level in generated_data:
        entries.append(
            evaluate_entry(
                source="GENERATED",
                entry_id=level["id"],
                name=level.get("name", level["id"]),
                state=state_from_coords(level["cue"], level["balls"]),
                max_depth=max_depth,
                max_states=max_states,
            )
        )

    return sorted(
        entries,
        key=lambda entry: (
            entry.scores.interestingness,
            entry.scores.difficulty,
            -entry.result.shortest_solution_count,
        ),
        reverse=True,
    )


def write_benchmark_json(path: Path, entries: list[BenchmarkEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([entry.to_dict() for entry in entries], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_benchmark(entries: list[BenchmarkEntry]) -> str:
    lines = [
        "CHAIN SHOT EVALUATOR v0.2 BENCHMARK",
        "Core 12 + generated Top 20, rescored from board state",
        "=" * 78,
        "RANK  SRC        ID          I      D    PAR SOL  T  CHAIN BC  NAME",
        "-" * 78,
    ]

    for rank, entry in enumerate(entries, start=1):
        lines.append(
            f"{rank:>4}  "
            f"{entry.source:<9}  "
            f"{entry.entry_id:<10}  "
            f"{entry.scores.interestingness:>5.1f}  "
            f"{entry.scores.difficulty:>5.1f}  "
            f"{entry.result.min_moves:>3} "
            f"{entry.result.shortest_solution_count:>3}  "
            f"{entry.metrics.temptation_count:>1}  "
            f"{entry.metrics.max_chain_capacity:>5} "
            f"{entry.metrics.built_chain_gain:>2}  "
            f"{entry.name}"
        )

    lines.append("")
    lines.append("CHAIN = true chain capacity; BC = built-chain gain under v0.2.")
    return "\n".join(lines) + "\n"


def write_benchmark_text(path: Path, entries: list[BenchmarkEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_benchmark(entries), encoding="utf-8")

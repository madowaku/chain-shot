from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .benchmark import BenchmarkEntry, evaluate_entry, state_from_coords
from .constants import BOARD_SIZE, CELL_COUNT, POCKET_CELLS
from .models import State, add_ball, cells_from_bitboard, has_ball, remove_ball
from .symmetry import canonical_key


MUTATION_OPERATORS = (
    "cue_relocate",
    "ball_relocate",
    "ball_add",
    "ball_remove",
)


@dataclass(frozen=True, slots=True)
class ParentSummary:
    parent_id: str
    parent_score: float
    requested: int
    unique_children: int
    solved_children: int
    beaters: int

    def to_dict(self) -> dict:
        return {
            "parentId": self.parent_id,
            "parentScore": self.parent_score,
            "requested": self.requested,
            "uniqueChildren": self.unique_children,
            "solvedChildren": self.solved_children,
            "beaters": self.beaters,
        }


@dataclass(frozen=True, slots=True)
class MutationEntry:
    parent_id: str
    operator: str
    child: BenchmarkEntry

    @property
    def improvement(self) -> float:
        return round(
            self.child.scores.interestingness - self.parent_score,
            1,
        )

    @property
    def parent_score(self) -> float:
        raise AttributeError("parent score is supplied during serialization")


@dataclass(frozen=True, slots=True)
class MutationBeater:
    parent_id: str
    parent_score: float
    operator: str
    child: BenchmarkEntry

    @property
    def improvement(self) -> float:
        return round(self.child.scores.interestingness - self.parent_score, 1)

    def to_dict(self) -> dict:
        data = self.child.to_dict()
        data["mutation"] = {
            "parentId": self.parent_id,
            "operator": self.operator,
            "parentInterestingness": self.parent_score,
            "improvement": self.improvement,
        }
        return data


@dataclass(frozen=True, slots=True)
class MutationRun:
    seed: int
    per_parent: int
    parents: tuple[BenchmarkEntry, ...]
    parent_summaries: tuple[ParentSummary, ...]
    beaters: tuple[MutationBeater, ...]

    def summary_dict(self) -> dict:
        return {
            "version": 1,
            "seed": self.seed,
            "perParent": self.per_parent,
            "parents": [summary.to_dict() for summary in self.parent_summaries],
            "totalBeaters": len(self.beaters),
        }


def _playable_cells() -> tuple[int, ...]:
    return tuple(cell for cell in range(CELL_COUNT) if cell not in POCKET_CELLS)


PLAYABLE_CELLS = _playable_cells()


def _adjacent_playable(cell: int) -> list[int]:
    row, col = divmod(cell, BOARD_SIZE)
    neighbors: list[int] = []
    for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
        nr, nc = row + dr, col + dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue
        next_cell = nr * BOARD_SIZE + nc
        if next_cell not in POCKET_CELLS:
            neighbors.append(next_cell)
    return neighbors


def _choose_destination(
    rng: random.Random,
    *,
    origin: int,
    occupied: set[int],
) -> int | None:
    local = [
        cell
        for cell in _adjacent_playable(origin)
        if cell not in occupied
    ]
    global_cells = [
        cell
        for cell in PLAYABLE_CELLS
        if cell not in occupied and cell != origin
    ]

    if local and rng.random() < 0.65:
        return rng.choice(local)
    if global_cells:
        return rng.choice(global_cells)
    return None


def mutate_state(
    parent: State,
    rng: random.Random,
    *,
    min_balls: int = 3,
    max_balls: int = 6,
) -> tuple[State, str]:
    balls = list(cells_from_bitboard(parent.balls))
    ball_count = len(balls)

    operators = ["cue_relocate", "ball_relocate"]
    if ball_count < max_balls:
        operators.append("ball_add")
    if ball_count > min_balls:
        operators.append("ball_remove")

    operator = rng.choice(operators)

    if operator == "cue_relocate":
        occupied = set(balls)
        destination = _choose_destination(
            rng,
            origin=parent.cue,
            occupied=occupied,
        )
        if destination is None:
            return parent, operator
        return State(cue=destination, balls=parent.balls), operator

    if operator == "ball_relocate":
        ball = rng.choice(balls)
        occupied = set(balls)
        occupied.remove(ball)
        occupied.add(parent.cue)
        destination = _choose_destination(
            rng,
            origin=ball,
            occupied=occupied,
        )
        if destination is None:
            return parent, operator
        moved = add_ball(remove_ball(parent.balls, ball), destination)
        return State(cue=parent.cue, balls=moved), operator

    if operator == "ball_add":
        occupied = set(balls)
        occupied.add(parent.cue)
        options = [cell for cell in PLAYABLE_CELLS if cell not in occupied]
        if not options:
            return parent, operator
        return State(
            cue=parent.cue,
            balls=add_ball(parent.balls, rng.choice(options)),
        ), operator

    ball = rng.choice(balls)
    return State(
        cue=parent.cue,
        balls=remove_ball(parent.balls, ball),
    ), operator


def load_top_generated_parents(
    path: Path,
    *,
    top_n: int = 3,
    max_depth: int = 12,
    max_states: int = 50_000,
) -> tuple[BenchmarkEntry, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    generated = [
        item for item in data
        if item.get("source") == "GENERATED"
    ]
    if not generated:
        generated = data

    parents: list[BenchmarkEntry] = []
    for item in generated[:top_n]:
        state = state_from_coords(item["cue"], item["balls"])
        parents.append(
            evaluate_entry(
                source="PARENT",
                entry_id=item["id"],
                name=item.get("name", item["id"]),
                state=state,
                max_depth=max_depth,
                max_states=max_states,
            )
        )
    return tuple(parents)


def run_mutation_search(
    *,
    parents: tuple[BenchmarkEntry, ...],
    per_parent: int = 500,
    seed: int = 20260921,
    min_moves: int = 4,
    max_moves: int = 12,
    max_states: int = 50_000,
) -> MutationRun:
    rng = random.Random(seed)
    global_seen = {canonical_key(parent.state) for parent in parents}
    beaters: list[MutationBeater] = []
    summaries: list[ParentSummary] = []

    for parent_index, parent in enumerate(parents, start=1):
        unique_children = 0
        solved_children = 0
        parent_beaters = 0

        for mutation_index in range(1, per_parent + 1):
            child_state, operator = mutate_state(parent.state, rng)
            key = canonical_key(child_state)
            if key in global_seen:
                continue
            global_seen.add(key)
            unique_children += 1

            try:
                child = evaluate_entry(
                    source="MUTATION",
                    entry_id=(
                        f"{parent.entry_id}-M{parent_index:02d}-{mutation_index:04d}"
                    ),
                    name=f"{parent.entry_id} / {operator}",
                    state=child_state,
                    max_depth=max_moves,
                    max_states=max_states,
                )
            except ValueError:
                continue

            if child.result.min_moves is None or child.result.min_moves < min_moves:
                continue

            solved_children += 1

            if child.scores.interestingness > parent.scores.interestingness:
                beaters.append(
                    MutationBeater(
                        parent_id=parent.entry_id,
                        parent_score=parent.scores.interestingness,
                        operator=operator,
                        child=child,
                    )
                )
                parent_beaters += 1

        summaries.append(
            ParentSummary(
                parent_id=parent.entry_id,
                parent_score=parent.scores.interestingness,
                requested=per_parent,
                unique_children=unique_children,
                solved_children=solved_children,
                beaters=parent_beaters,
            )
        )

    beaters.sort(
        key=lambda entry: (
            entry.child.scores.interestingness,
            entry.improvement,
            entry.child.scores.difficulty,
            -entry.child.result.shortest_solution_count,
        ),
        reverse=True,
    )

    return MutationRun(
        seed=seed,
        per_parent=per_parent,
        parents=parents,
        parent_summaries=tuple(summaries),
        beaters=tuple(beaters),
    )


def write_mutation_run(output_dir: Path, run: MutationRun) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "summary.json").write_text(
        json.dumps(run.summary_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "parent_beaters.json").write_text(
        json.dumps(
            [beater.to_dict() for beater in run.beaters],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "parent_beaters.txt").write_text(
        render_mutation_run(run),
        encoding="utf-8",
    )


def render_mutation_run(run: MutationRun, *, limit: int = 20) -> str:
    lines = [
        "CHAIN SHOT MUTATION GENERATOR v0.1",
        f"Seed={run.seed}  PerParent={run.per_parent}",
        "=" * 86,
    ]
    for summary in run.parent_summaries:
        lines.append(
            f"{summary.parent_id}: "
            f"I={summary.parent_score:.1f}  "
            f"unique={summary.unique_children}  "
            f"solved={summary.solved_children}  "
            f"beaters={summary.beaters}"
        )

    lines.extend(
        [
            "",
            "RANK  PARENT       CHILD                 I     +I     D   PAR SOL T CHAIN BC  OP",
            "-" * 86,
        ]
    )

    for rank, beater in enumerate(run.beaters[:limit], start=1):
        child = beater.child
        lines.append(
            f"{rank:>4}  "
            f"{beater.parent_id:<11}  "
            f"{child.entry_id:<20}  "
            f"{child.scores.interestingness:>5.1f} "
            f"{beater.improvement:>5.1f} "
            f"{child.scores.difficulty:>5.1f} "
            f"{child.result.min_moves:>3} "
            f"{child.result.shortest_solution_count:>3} "
            f"{child.metrics.temptation_count:>1} "
            f"{child.metrics.max_chain_capacity:>5} "
            f"{child.metrics.built_chain_gain:>2}  "
            f"{beater.operator}"
        )

    if not run.beaters:
        lines.append("(no parent-beating mutations found)")

    return "\n".join(lines) + "\n"

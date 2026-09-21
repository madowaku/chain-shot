from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .benchmark import BenchmarkEntry, evaluate_entry
from .models import State, cells_from_bitboard
from .mutation import load_top_generated_parents, mutate_state_v2
from .review import render_board
from .symmetry import canonical_key


@dataclass(frozen=True, slots=True)
class EvolutionNode:
    root_id: str
    root_score: float
    generation: int
    parent_id: str
    parent_score: float
    operator: str
    parent_state: State
    child: BenchmarkEntry

    @property
    def improvement_from_parent(self) -> float:
        return round(self.child.scores.interestingness - self.parent_score, 1)

    @property
    def improvement_from_root(self) -> float:
        return round(self.child.scores.interestingness - self.root_score, 1)

    def to_dict(self) -> dict:
        data = self.child.to_dict()
        data["evolution"] = {
            "rootId": self.root_id,
            "generation": self.generation,
            "parentId": self.parent_id,
            "operator": self.operator,
            "parentInterestingness": self.parent_score,
            "rootInterestingness": self.root_score,
            "improvementFromParent": self.improvement_from_parent,
            "improvementFromRoot": self.improvement_from_root,
        }
        return data


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    generation: int
    parents: int
    requested_per_parent: int
    unique_children: int
    solved_children: int
    beaters: int

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "parents": self.parents,
            "requestedPerParent": self.requested_per_parent,
            "uniqueChildren": self.unique_children,
            "solvedChildren": self.solved_children,
            "beaters": self.beaters,
        }


@dataclass(frozen=True, slots=True)
class EvolutionRun:
    seed: int
    roots: tuple[BenchmarkEntry, ...]
    generation_summaries: tuple[GenerationSummary, ...]
    beaters: tuple[EvolutionNode, ...]
    elites: tuple[EvolutionNode, ...]

    def summary_dict(self) -> dict:
        return {
            "version": 2,
            "seed": self.seed,
            "roots": [
                {
                    "id": root.entry_id,
                    "interestingness": root.scores.interestingness,
                    "difficulty": root.scores.difficulty,
                }
                for root in self.roots
            ],
            "generations": [
                summary.to_dict() for summary in self.generation_summaries
            ],
            "totalBeaters": len(self.beaters),
            "eliteCount": len(self.elites),
        }


@dataclass(frozen=True, slots=True)
class _ParentRef:
    root_id: str
    root_score: float
    entry: BenchmarkEntry


def _rank_key(node: EvolutionNode) -> tuple:
    child = node.child
    return (
        child.scores.interestingness,
        child.result.shortest_solution_count == 1,
        child.metrics.max_chain_capacity,
        child.metrics.built_chain_gain,
        node.improvement_from_root,
        child.scores.difficulty,
    )


def _select_elites(
    nodes: list[EvolutionNode],
    *,
    per_root: int,
) -> tuple[EvolutionNode, ...]:
    grouped: dict[str, list[EvolutionNode]] = {}
    for node in nodes:
        grouped.setdefault(node.root_id, []).append(node)

    selected: list[EvolutionNode] = []
    for root_id in sorted(grouped):
        group = sorted(grouped[root_id], key=_rank_key, reverse=True)
        unique = [
            node for node in group
            if node.child.result.shortest_solution_count == 1
        ]
        pool = unique if unique else group
        selected.extend(pool[:per_root])

    return tuple(sorted(selected, key=_rank_key, reverse=True))


def _spawn_generation(
    *,
    parents: tuple[_ParentRef, ...],
    generation: int,
    per_parent: int,
    rng: random.Random,
    seen: set[tuple[int, int]],
    min_moves: int,
    max_moves: int,
    max_states: int,
) -> tuple[list[EvolutionNode], GenerationSummary]:
    beaters: list[EvolutionNode] = []
    unique_children = 0
    solved_children = 0

    for parent_index, parent_ref in enumerate(parents, start=1):
        parent = parent_ref.entry

        for mutation_index in range(1, per_parent + 1):
            child_state, operator = mutate_state_v2(parent.state, rng)
            key = canonical_key(child_state)
            if key in seen:
                continue
            seen.add(key)
            unique_children += 1

            try:
                child = evaluate_entry(
                    source="EVOLUTION",
                    entry_id=(
                        f"{parent_ref.root_id}-G{generation}-"
                        f"{parent_index:02d}-{mutation_index:04d}"
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

            if child.scores.interestingness <= parent.scores.interestingness:
                continue

            beaters.append(
                EvolutionNode(
                    root_id=parent_ref.root_id,
                    root_score=parent_ref.root_score,
                    generation=generation,
                    parent_id=parent.entry_id,
                    parent_score=parent.scores.interestingness,
                    operator=operator,
                    parent_state=parent.state,
                    child=child,
                )
            )

    summary = GenerationSummary(
        generation=generation,
        parents=len(parents),
        requested_per_parent=per_parent,
        unique_children=unique_children,
        solved_children=solved_children,
        beaters=len(beaters),
    )
    return beaters, summary


def run_evolution_search(
    *,
    roots: tuple[BenchmarkEntry, ...],
    first_generation_per_parent: int = 500,
    second_generation_per_parent: int = 250,
    elites_per_root: int = 2,
    seed: int = 20260921,
    min_moves: int = 4,
    max_moves: int = 12,
    max_states: int = 50_000,
) -> EvolutionRun:
    rng = random.Random(seed)
    seen = {canonical_key(root.state) for root in roots}

    root_refs = tuple(
        _ParentRef(
            root_id=root.entry_id,
            root_score=root.scores.interestingness,
            entry=root,
        )
        for root in roots
    )

    gen1, summary1 = _spawn_generation(
        parents=root_refs,
        generation=1,
        per_parent=first_generation_per_parent,
        rng=rng,
        seen=seen,
        min_moves=min_moves,
        max_moves=max_moves,
        max_states=max_states,
    )

    gen1_elites = _select_elites(gen1, per_root=elites_per_root)
    gen2_parents = tuple(
        _ParentRef(
            root_id=node.root_id,
            root_score=node.root_score,
            entry=node.child,
        )
        for node in gen1_elites
    )

    if gen2_parents and second_generation_per_parent > 0:
        gen2, summary2 = _spawn_generation(
            parents=gen2_parents,
            generation=2,
            per_parent=second_generation_per_parent,
            rng=rng,
            seen=seen,
            min_moves=min_moves,
            max_moves=max_moves,
            max_states=max_states,
        )
    else:
        gen2 = []
        summary2 = GenerationSummary(
            generation=2,
            parents=0,
            requested_per_parent=second_generation_per_parent,
            unique_children=0,
            solved_children=0,
            beaters=0,
        )

    all_beaters = sorted(gen1 + gen2, key=_rank_key, reverse=True)
    final_elites = _select_elites(all_beaters, per_root=elites_per_root)

    return EvolutionRun(
        seed=seed,
        roots=roots,
        generation_summaries=(summary1, summary2),
        beaters=tuple(all_beaters),
        elites=final_elites,
    )


def load_evolution_roots(
    path: Path,
    *,
    top_n: int = 3,
    max_depth: int = 12,
    max_states: int = 50_000,
) -> tuple[BenchmarkEntry, ...]:
    return load_top_generated_parents(
        path,
        top_n=top_n,
        max_depth=max_depth,
        max_states=max_states,
    )


def _state_diff(parent: State, child: State) -> str:
    parent_balls = set(cells_from_bitboard(parent.balls))
    child_balls = set(cells_from_bitboard(child.balls))
    added = sorted(child_balls - parent_balls)
    removed = sorted(parent_balls - child_balls)

    parts: list[str] = []
    if parent.cue != child.cue:
        parts.append(
            f"cue {divmod(parent.cue, 7)} -> {divmod(child.cue, 7)}"
        )
    if added:
        parts.append("+" + ", ".join(str(divmod(cell, 7)) for cell in added))
    if removed:
        parts.append("-" + ", ".join(str(divmod(cell, 7)) for cell in removed))
    return "; ".join(parts) if parts else "(no visible diff)"


def render_evolution_run(run: EvolutionRun, *, limit: int = 20) -> str:
    lines = [
        "CHAIN SHOT MUTATION GENERATOR v0.2",
        f"Seed={run.seed}",
        "=" * 96,
    ]

    for summary in run.generation_summaries:
        lines.append(
            f"Generation {summary.generation}: "
            f"parents={summary.parents}  "
            f"perParent={summary.requested_per_parent}  "
            f"unique={summary.unique_children}  "
            f"solved={summary.solved_children}  "
            f"beaters={summary.beaters}"
        )

    lines.extend(
        [
            "",
            "RANK GEN ROOT         PARENT               CHILD                    I    +ROOT  PAR SOL T CHAIN BC OP",
            "-" * 96,
        ]
    )

    for rank, node in enumerate(run.beaters[:limit], start=1):
        child = node.child
        lines.append(
            f"{rank:>4} {node.generation:>3} "
            f"{node.root_id:<12} "
            f"{node.parent_id:<20} "
            f"{child.entry_id:<24} "
            f"{child.scores.interestingness:>5.1f} "
            f"{node.improvement_from_root:>6.1f} "
            f"{child.result.min_moves:>3} "
            f"{child.result.shortest_solution_count:>3} "
            f"{child.metrics.temptation_count:>1} "
            f"{child.metrics.max_chain_capacity:>5} "
            f"{child.metrics.built_chain_gain:>2} "
            f"{node.operator}"
        )

    if not run.beaters:
        lines.append("(no parent-beating mutations found)")

    return "\n".join(lines) + "\n"


def render_lineage_review(run: EvolutionRun, *, limit: int = 10) -> str:
    blocks: list[str] = [
        "CHAIN SHOT MUTATION v0.2 LINEAGE REVIEW",
        "Legend: W=cue  o=object  O=pocket  .=empty",
        "=" * 64,
        "",
    ]

    for rank, node in enumerate(run.beaters[:limit], start=1):
        child = node.child
        solution = " ".join(
            direction.name for direction in child.result.sample_solutions[0]
        )
        blocks.extend(
            [
                f"#{rank:02d} {child.entry_id}",
                (
                    f"Root={node.root_id}  Gen={node.generation}  "
                    f"Parent={node.parent_id}  OP={node.operator}"
                ),
                (
                    f"I {node.parent_score:.1f} -> "
                    f"{child.scores.interestingness:.1f}  "
                    f"(+parent {node.improvement_from_parent:.1f}, "
                    f"+root {node.improvement_from_root:.1f})"
                ),
                (
                    f"PAR={child.result.min_moves}  "
                    f"SOL={child.result.shortest_solution_count}  "
                    f"T={child.metrics.temptation_count}  "
                    f"CHAIN={child.metrics.max_chain_capacity}  "
                    f"BC=+{child.metrics.built_chain_gain}"
                ),
                f"Diff: {_state_diff(node.parent_state, child.state)}",
                "",
                "PARENT",
                render_board(node.parent_state),
                "",
                "CHILD",
                render_board(child.state),
                "",
                f"Solution: {solution}",
                "",
                "-" * 64,
                "",
            ]
        )

    return "\n".join(blocks)


def write_evolution_run(output_dir: Path, run: EvolutionRun) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "summary.json").write_text(
        json.dumps(run.summary_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "all_beaters.json").write_text(
        json.dumps(
            [node.to_dict() for node in run.beaters],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "top_20.json").write_text(
        json.dumps(
            [node.to_dict() for node in run.beaters[:20]],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "elite.json").write_text(
        json.dumps(
            [node.to_dict() for node in run.elites],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "ranking.txt").write_text(
        render_evolution_run(run),
        encoding="utf-8",
    )
    (output_dir / "lineage_review.txt").write_text(
        render_lineage_review(run),
        encoding="utf-8",
    )

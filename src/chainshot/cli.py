from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import benchmark_core_and_generated, render_benchmark, write_benchmark_json, write_benchmark_text
from .constants import to_cell
from .evolution import load_evolution_roots, render_evolution_run, run_evolution_search, write_evolution_run
from .generator import generate_candidates
from .models import State, bitboard_from_cells
from .mutation import load_top_generated_parents, render_mutation_run, run_mutation_search, write_mutation_run
from .review import render_top_dicts
from .serializer import write_candidates_ascii, write_candidates_json, write_candidates_jsonl, write_summary_json
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


def _cmd_generate(
    *,
    count: int,
    seed: int,
    min_moves: int,
    max_moves: int,
    max_states: int,
    ball_count: int | None,
    output_dir: Path,
) -> int:
    candidates, summary = generate_candidates(
        count=count,
        seed=seed,
        min_moves=min_moves,
        max_moves=max_moves,
        max_states=max_states,
        ball_count=ball_count,
    )

    write_candidates_jsonl(output_dir / "candidates.jsonl", candidates)
    write_candidates_jsonl(
        output_dir / "unique.jsonl",
        [candidate for candidate in candidates if candidate.solve_result.shortest_solution_count == 1],
    )
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            candidate.scores.interestingness,
            candidate.scores.difficulty,
            -(candidate.solve_result.shortest_solution_count),
        ),
        reverse=True,
    )
    write_candidates_json(output_dir / "top_20.json", ranked[:20])
    write_candidates_ascii(output_dir / "top_20.txt", ranked[:20])
    write_summary_json(output_dir / "summary.json", summary)

    print("CHAIN SHOT LEVEL GENERATOR v0.1")
    print()
    print(f"Seed: {summary.seed}")
    print(f"Requested: {summary.requested:,}")
    print(f"Generated unique: {summary.generated:,}")
    print(f"Duplicates: {summary.duplicates:,}")
    print(f"Exhausted: {summary.exhausted:,}")
    print(f"Unsolved / >{max_moves} moves: {summary.unsolved_or_too_hard:,}")
    print(f"Too easy (<{min_moves} moves): {summary.too_easy:,}")
    print(f"Candidates: {summary.candidates:,}")
    print(f"Unique candidates: {summary.unique_candidates:,}")
    print()
    print("PAR distribution:", summary.par_distribution)
    print("Ball-count distribution:", summary.ball_count_distribution)
    print("Solution-count distribution:", summary.solution_count_distribution)
    print()
    if ranked:
        print("Top candidates:")
        for rank, candidate in enumerate(ranked[:5], start=1):
            print(
                f"  {rank:02d}. {candidate.candidate_id} "
                f"I={candidate.scores.interestingness:.1f} "
                f"D={candidate.scores.difficulty:.1f} "
                f"PAR={candidate.solve_result.min_moves} "
                f"SOL={candidate.solve_result.shortest_solution_count} "
                f"T={candidate.metrics.temptation_count} "
                f"BC=+{candidate.metrics.built_chain_gain}"
            )
        print()
    print(f"Output: {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chainshot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve a JSON level with BFS")
    solve_parser.add_argument("path", type=Path)
    solve_parser.add_argument("--max-depth", type=int, default=12)
    solve_parser.add_argument("--max-states", type=int, default=50_000)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate random boards, remove symmetric duplicates, and keep BFS candidates",
    )
    generate_parser.add_argument("--count", type=int, default=10_000)
    generate_parser.add_argument("--seed", type=int, default=20260921)
    generate_parser.add_argument("--min-moves", type=int, default=4)
    generate_parser.add_argument("--max-moves", type=int, default=12)
    generate_parser.add_argument("--max-states", type=int, default=50_000)
    generate_parser.add_argument(
        "--balls",
        type=int,
        choices=(3, 4, 5, 6),
        default=None,
        help="Force an exact object-ball count. Default uses weighted 3-6 generation.",
    )
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Default: output/run_<seed>",
    )
    review_parser = subparsers.add_parser(
        "review",
        help="Render ranked candidate JSON as an ASCII board review",
    )
    review_parser.add_argument("path", type=Path)
    review_parser.add_argument("--limit", type=int, default=20)

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Rescore Core 12 and generated Top 20 with Evaluator v0.2",
    )
    benchmark_parser.add_argument(
        "--generated",
        type=Path,
        required=True,
        help="Path to a generated top_20.json file",
    )
    benchmark_parser.add_argument(
        "--core",
        type=Path,
        default=Path("fixtures") / "core12.json",
    )
    benchmark_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Default: alongside generated JSON in benchmark_v02/",
    )
    benchmark_parser.add_argument("--max-depth", type=int, default=12)
    benchmark_parser.add_argument("--max-states", type=int, default=50_000)

    mutate_parser = subparsers.add_parser(
        "mutate",
        help="Mutate top generated benchmark parents and keep only parent-beating children",
    )
    mutate_parser.add_argument(
        "--parents",
        type=Path,
        required=True,
        help="Path to benchmark_v02/combined_ranking.json",
    )
    mutate_parser.add_argument("--top", type=int, default=3)
    mutate_parser.add_argument("--per-parent", type=int, default=500)
    mutate_parser.add_argument("--seed", type=int, default=20260921)
    mutate_parser.add_argument("--min-moves", type=int, default=4)
    mutate_parser.add_argument("--max-moves", type=int, default=12)
    mutate_parser.add_argument("--max-states", type=int, default=50_000)
    mutate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Default: alongside parent benchmark in mutation_v01/",
    )

    evolve_parser = subparsers.add_parser(
        "evolve",
        help="Run two-generation, identity-biased Mutation v0.2 search",
    )
    evolve_parser.add_argument(
        "--parents",
        type=Path,
        required=True,
        help="Path to benchmark_v02/combined_ranking.json",
    )
    evolve_parser.add_argument("--top", type=int, default=3)
    evolve_parser.add_argument("--first-generation", type=int, default=500)
    evolve_parser.add_argument("--second-generation", type=int, default=250)
    evolve_parser.add_argument("--elites-per-root", type=int, default=2)
    evolve_parser.add_argument("--seed", type=int, default=20260921)
    evolve_parser.add_argument("--min-moves", type=int, default=4)
    evolve_parser.add_argument("--max-moves", type=int, default=12)
    evolve_parser.add_argument("--max-states", type=int, default=50_000)
    evolve_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Default: alongside parent benchmark in mutation_v02/",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "solve":
        return _cmd_solve(args.path, args.max_depth, args.max_states)

    if args.command == "review":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        print(render_top_dicts(data, limit=args.limit), end="")
        return 0

    if args.command == "benchmark":
        entries = benchmark_core_and_generated(
            core_path=args.core,
            generated_path=args.generated,
            max_depth=args.max_depth,
            max_states=args.max_states,
        )
        output_dir = args.output or args.generated.parent / "benchmark_v02"
        write_benchmark_json(output_dir / "combined_ranking.json", entries)
        write_benchmark_text(output_dir / "combined_ranking.txt", entries)
        print(render_benchmark(entries), end="")
        print(f"Output: {output_dir}")
        return 0

    if args.command == "mutate":
        parents = load_top_generated_parents(
            args.parents,
            top_n=args.top,
            max_depth=args.max_moves,
            max_states=args.max_states,
        )
        run = run_mutation_search(
            parents=parents,
            per_parent=args.per_parent,
            seed=args.seed,
            min_moves=args.min_moves,
            max_moves=args.max_moves,
            max_states=args.max_states,
        )
        output_dir = args.output or args.parents.parent / "mutation_v01"
        write_mutation_run(output_dir, run)
        print(render_mutation_run(run), end="")
        print(f"Output: {output_dir}")
        return 0

    if args.command == "evolve":
        roots = load_evolution_roots(
            args.parents,
            top_n=args.top,
            max_depth=args.max_moves,
            max_states=args.max_states,
        )
        run = run_evolution_search(
            roots=roots,
            first_generation_per_parent=args.first_generation,
            second_generation_per_parent=args.second_generation,
            elites_per_root=args.elites_per_root,
            seed=args.seed,
            min_moves=args.min_moves,
            max_moves=args.max_moves,
            max_states=args.max_states,
        )
        output_dir = args.output or args.parents.parent / "mutation_v02"
        write_evolution_run(output_dir, run)
        print(render_evolution_run(run), end="")
        print(f"Output: {output_dir}")
        return 0

    if args.command == "generate":
        output_dir = args.output or Path("output") / f"run_{args.seed}"
        return _cmd_generate(
            count=args.count,
            seed=args.seed,
            min_moves=args.min_moves,
            max_moves=args.max_moves,
            max_states=args.max_states,
            ball_count=args.balls,
            output_dir=output_dir,
        )

    parser.error("unknown command")
    return 2

# CHAIN SHOT

A straight-line billiards logic puzzle prototype.

The v0.1 rule set is deliberately tiny: choose one of four directions, move in a straight line, transfer motion through collisions, and sink every object ball. There is no angle, power control, spin, or rail reflection.

## Current milestone

**Level Generator v0.1**

The repository currently contains:

- an immutable 49-bit board state
- the authoritative straight-shot simulator
- cue scratch / pocket handling
- chained motion transfer through object balls
- BFS shortest-path solving
- exact counting of shortest action sequences
- basic simulator and solver regression tests
- a CLI for solving JSON levels

Next: encode the hand-authored Core 12, then build seeded generation, symmetry deduplication, and CHAIN SHOT-specific interestingness metrics.

## Setup

    python -m pip install -e ".[dev]"
    pytest

## Solve a level

    chainshot solve examples/first_hit.json

or:

    python -m chainshot solve examples/first_hit.json

Expected result for the example:

    Solved: YES
    Minimum moves: 1
    Shortest solutions: 1
    Solution:
    UP

## Architecture

The simulator is the only source of truth for game rules.

- Generator creates candidate boards.
- Solver returns mathematical facts.
- Analyzer extracts structural features.
- Evaluator ranks candidates.
- Human playtesting decides which levels are actually good.

See `TASKS.md` for the Level Generator v0.1 roadmap.

## Generate candidate levels

Run a small smoke test first:

    python -m chainshot generate --count 100 --seed 20260921

Then run the first mining batch:

    python -m chainshot generate --count 10000 --seed 20260921

Generation uses the weighted object-ball distribution 3/4/5/6 = 20%/30%/30%/20%, removes duplicates under the four table-preserving symmetries, solves each unique board with BFS, and keeps only boards whose minimum solution length is 4-12 moves.

Outputs are written to:

    output/run_<seed>/candidates.jsonl
    output/run_<seed>/summary.json

To force a specific ball count:

    python -m chainshot generate --count 1000 --seed 20260921 --balls 5

## Candidate statistics and Phase 4 metrics

Each generation run now writes three files:

    output/run_<seed>/candidates.jsonl
    output/run_<seed>/unique.jsonl
    output/run_<seed>/summary.json

The summary includes:

- PAR distribution
- object-ball-count distribution
- shortest-solution-count distribution
- unique-solution candidate count

Each candidate also carries trace-derived metrics:

- sink delay
- setup shots
- cue-only reposition shots
- object-ball transport distance
- max / average collision cascade
- initial / maximum cascade capacity
- built-chain gain
- direction diversity
- endgame sinks and sink streak

These metrics are computed only after a board survives the BFS candidate filter, keeping bulk generation cheap.

## Phase 4 ranking

Candidate analysis now includes:

- temptationCount
- difficultyScore
- interestingnessScore

A temptation is an immediately available sinking action that cannot preserve the current optimal remaining shot budget. It may be a true dead end or simply a slower route; both are useful as "don't take the obvious sink" signals.

Difficulty and interestingness are intentionally separate. Difficulty emphasizes solution depth and BFS search complexity. Interestingness emphasizes CHAIN SHOT-specific structure such as built chains, setup shots, temptation traps, transport, cascades, and endgame payoff.

Each generation run also writes:

    output/run_<seed>/top_20.json

This file is ranked by provisional interestingness, then difficulty. The weights are heuristics for triage, not claims about fun. Human playtesting should retune them.

## Evaluator v0.2 benchmark

Evaluator v0.2 treats a single cue-to-object collision as setup, not a chain.

    true chain capacity = max(0, collision count - 1)

Examples:

    0 collisions -> chain 0
    1 collision  -> chain 0
    2 collisions -> chain 1
    3 collisions -> chain 2

Built-chain gain now compares this true chain capacity across the optimal path. Interestingness v0.2 also penalizes boards that never create a true multi-ball chain.

To rescore the hand-authored Core 12 and an existing generated Top 20 from board state with exactly the same evaluator:

    python -m chainshot benchmark --generated output/run_20260921/top_20.json

The old scores stored in top_20.json are ignored. Every board is solved and analyzed again.

Outputs:

    output/run_20260921/benchmark_v02/combined_ranking.json
    output/run_20260921/benchmark_v02/combined_ranking.txt

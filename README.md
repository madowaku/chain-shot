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

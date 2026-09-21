# CHAIN SHOT Level Generator v0.1

## Goal

Build a level-mining pipeline:

random board -> exact BFS solve -> feature analysis -> interestingness ranking -> Top 100

## Phase 1: Core engine

- [x] Python 3.12+ package scaffold
- [x] Immutable bitboard State
- [x] Four-direction Action model
- [x] Single authoritative shot simulator
- [x] Cue scratch handling
- [x] Collision / motion-transfer chain handling
- [x] Shot trace counters
- [x] BFS shortest-path solver
- [x] Exact shortest-solution counting
- [x] Basic simulator tests
- [x] Basic solver tests

## Phase 2: Core 12 regression

- [x] Encode the hand-authored Core 12 as fixtures/core12.json
- [x] Verify every expected PAR with the BFS solver
- [x] Verify shortest-solution counts
- [x] Add regression tests so rule changes cannot silently break the Core 12

## Phase 3: Generator

- [x] Seeded random board generation
- [x] Object-ball distribution: 3-6 balls
- [x] Symmetry canonicalization: identity / horizontal / vertical / 180 degrees
- [x] Duplicate filtering
- [x] Candidate range: 4-12 minimum moves
- [x] JSONL output

## Phase 4: CHAIN SHOT metrics

- [x] Sink delay
- [x] Setup shots
- [x] Cue reposition shots
- [x] Ball transport distance
- [x] Max / average cascade
- [x] Built-chain gain
- [x] Temptation traps
- [x] Direction diversity
- [x] Endgame payoff
- [x] Difficulty score
- [x] Interestingness score

## Phase 5: Mining run

- [x] Export Top 20 by provisional interestingness

- [x] Generate 10,000 boards
- [ ] Export unique-solution candidates
- [ ] Export Top 100
- [ ] Human-rate at least 20 candidates
- [ ] Find 3-5 candidates worth joining/replacing the Core 12

## Architecture rules

1. Simulator is the only source of truth for game rules.
2. Solver only consumes State -> Action -> successor transitions.
3. Generator creates candidates. It does not decide what is fun.
4. Evaluator ranks candidates. Human playtesting makes final selections.
5. Any rule change must run the Core 12 regression suite first.

## Evaluator v0.2 calibration

- [x] Define true chain capacity: max(0, collision count - 1)
- [x] Rebase built-chain gain on true chain capacity
- [x] Add CHAIN SHOT identity penalties for no-chain boards
- [x] Add mixed Core 12 + generated Top 20 benchmark

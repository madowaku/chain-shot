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

- [ ] Encode the hand-authored Core 12 as fixtures/core12.json
- [ ] Verify every expected PAR with the BFS solver
- [ ] Verify shortest-solution counts
- [ ] Add regression tests so rule changes cannot silently break the Core 12

## Phase 3: Generator

- [ ] Seeded random board generation
- [ ] Object-ball distribution: 3-6 balls
- [ ] Symmetry canonicalization: identity / horizontal / vertical / 180 degrees
- [ ] Duplicate filtering
- [ ] Candidate range: 4-12 minimum moves
- [ ] JSONL output

## Phase 4: CHAIN SHOT metrics

- [ ] Sink delay
- [ ] Setup shots
- [ ] Cue reposition shots
- [ ] Ball transport distance
- [ ] Max / average cascade
- [ ] Built-chain gain
- [ ] Temptation traps
- [ ] Direction diversity
- [ ] Endgame payoff
- [ ] Difficulty score
- [ ] Interestingness score

## Phase 5: Mining run

- [ ] Generate 10,000 boards
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

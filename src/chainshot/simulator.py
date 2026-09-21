from __future__ import annotations

from .constants import POCKET_CELLS
from .models import (
    Direction,
    MotionSegment,
    ShotResult,
    ShotTrace,
    State,
    add_ball,
    has_ball,
    remove_ball,
    step_cell,
)


def simulate_shot(state: State, direction: Direction, *, trace: bool = False) -> ShotResult:
    """Simulate one straight shot.

    Motion never changes direction. When a moving ball hits an object ball,
    the mover stops immediately before the struck ball and motion transfers
    to the struck ball. An object ball entering a pocket disappears and ends
    the shot. A cue ball entering a pocket makes the entire action illegal.
    """

    cue = state.cue
    balls = state.balls

    mover_is_cue = True
    position = cue
    segment_start = position

    sunk_count = 0
    collision_count = 0
    cue_distance = 0
    object_distance = 0
    segments: list[MotionSegment] = []

    while True:
        next_cell = step_cell(position, direction)

        if next_cell is None:
            if mover_is_cue:
                cue = position
            else:
                balls = add_ball(balls, position)

            if trace:
                segments.append(
                    MotionSegment(
                        mover="CUE" if mover_is_cue else "OBJECT",
                        start=segment_start,
                        end=position,
                        distance=_segment_distance(segment_start, position),
                        outcome="RAIL",
                    )
                )
            break

        if next_cell in POCKET_CELLS:
            if mover_is_cue:
                return ShotResult(
                    legal=False,
                    changed=False,
                    next_state=None,
                    sunk_count=0,
                    collision_count=collision_count,
                    cue_distance=cue_distance,
                    object_distance=object_distance,
                    trace=_make_trace(segments, sunk_count, collision_count) if trace else None,
                )

            object_distance += 1
            sunk_count += 1
            if trace:
                segments.append(
                    MotionSegment(
                        mover="OBJECT",
                        start=segment_start,
                        end=next_cell,
                        distance=_segment_distance(segment_start, next_cell),
                        outcome="POCKET",
                    )
                )
            break

        if has_ball(balls, next_cell):
            if mover_is_cue:
                cue = position
            else:
                balls = add_ball(balls, position)

            if trace:
                segments.append(
                    MotionSegment(
                        mover="CUE" if mover_is_cue else "OBJECT",
                        start=segment_start,
                        end=position,
                        distance=_segment_distance(segment_start, position),
                        outcome="COLLISION",
                    )
                )

            balls = remove_ball(balls, next_cell)
            collision_count += 1
            mover_is_cue = False
            position = next_cell
            segment_start = next_cell
            continue

        position = next_cell
        if mover_is_cue:
            cue_distance += 1
        else:
            object_distance += 1

    next_state = State(cue=cue, balls=balls)
    changed = next_state != state

    return ShotResult(
        legal=True,
        changed=changed,
        next_state=next_state,
        sunk_count=sunk_count,
        collision_count=collision_count,
        cue_distance=cue_distance,
        object_distance=object_distance,
        trace=_make_trace(segments, sunk_count, collision_count) if trace else None,
    )


def _segment_distance(start: int, end: int) -> int:
    start_row, start_col = divmod(start, 7)
    end_row, end_col = divmod(end, 7)
    return abs(start_row - end_row) + abs(start_col - end_col)


def _make_trace(
    segments: list[MotionSegment], sunk_count: int, collision_count: int
) -> ShotTrace:
    return ShotTrace(
        segments=tuple(segments),
        sunk_count=sunk_count,
        collision_count=collision_count,
    )

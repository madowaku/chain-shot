from __future__ import annotations

import json
from pathlib import Path

from chainshot.generator import generate_candidates
from chainshot.serializer import write_candidates_jsonl, write_summary_json


def test_generator_serialization(tmp_path: Path) -> None:
    candidates, summary = generate_candidates(
        count=20,
        seed=4242,
        min_moves=4,
        max_moves=12,
        ball_count=3,
    )

    candidates_path = tmp_path / "candidates.jsonl"
    summary_path = tmp_path / "summary.json"

    write_candidates_jsonl(candidates_path, candidates)
    write_summary_json(summary_path, summary)

    lines = [line for line in candidates_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == len(candidates)

    if lines:
        first = json.loads(lines[0])
        assert "cue" in first
        assert "balls" in first
        assert 4 <= first["analysis"]["minMoves"] <= 12

    saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved_summary["seed"] == 4242
    assert saved_summary["requested"] == 20

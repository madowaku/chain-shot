from __future__ import annotations

import json
from pathlib import Path

from chainshot.benchmark import benchmark_core_and_generated, render_benchmark


def test_benchmark_rescores_core_and_generated_with_same_evaluator(tmp_path: Path) -> None:
    core_path = tmp_path / "core.json"
    generated_path = tmp_path / "top_20.json"

    core_path.write_text(
        json.dumps(
            {
                "levels": [
                    {
                        "id": "CORE-X",
                        "name": "CORE TEST",
                        "cue": [5, 3],
                        "balls": [[3, 3]],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    generated_path.write_text(
        json.dumps(
            [
                {
                    "id": "GEN-X",
                    "cue": [4, 6],
                    "balls": [[2, 6], [3, 6]],
                }
            ]
        ),
        encoding="utf-8",
    )

    entries = benchmark_core_and_generated(
        core_path=core_path,
        generated_path=generated_path,
    )

    assert {entry.source for entry in entries} == {"CORE", "GENERATED"}
    assert all(entry.scores.evaluator_version == "0.2" for entry in entries)

    text = render_benchmark(entries)
    assert "EVALUATOR v0.2 BENCHMARK" in text
    assert "CORE-X" in text
    assert "GEN-X" in text
    assert "CHAIN" in text

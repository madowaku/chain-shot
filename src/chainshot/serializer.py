from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .generator import Candidate, GenerationSummary


def write_candidates_jsonl(path: Path, candidates: Iterable[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.to_dict(), ensure_ascii=False))
            handle.write("\n")


def write_summary_json(path: Path, summary: GenerationSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_candidates_json(path: Path, candidates: Iterable[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [candidate.to_dict() for candidate in candidates]
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

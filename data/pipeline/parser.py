"""raw/laws/*.txt -> processed/laws.jsonl (articles split by number).

Starter parser.py goes here (it was not in the repo at scaffold time).
"""
from pathlib import Path

from .schemas import LawRec


def parse_law(path: Path, former_names: list[str]) -> LawRec:
    raise NotImplementedError("TODO(member 3): split into articles, set parent_number")

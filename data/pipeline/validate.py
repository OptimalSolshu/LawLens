"""Validate a processed/ directory against contracts/data-format.md.

Usage: python -m pipeline.validate processed
"""
import re
import sys
from pathlib import Path

from pydantic import TypeAdapter

from .ids import article_id
from .schemas import JSONL, DraftRec, InternationalFile, LawRec


def validate_dir(d: Path) -> list[str]:
    """Return a list of problems (empty = valid). Missing files are skipped."""
    errors: list[str] = []
    for name, model in JSONL.items():
        path = d / name
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = model.model_validate_json(line)
            except ValueError as e:
                errors.append(f"{name}:{i}: {e}")
                continue
            if isinstance(rec, LawRec):
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rec.law_id):
                    errors.append(f"{name}:{i}: law_id {rec.law_id!r} is not an ASCII slug")
                for a in rec.articles:
                    if a.article_id != article_id(rec.law_id, a.number):
                        errors.append(f"{name}:{i}: bad article_id {a.article_id!r}")
    if (d / "drafts.json").exists():
        try:
            TypeAdapter(list[DraftRec]).validate_json((d / "drafts.json").read_bytes())
        except ValueError as e:
            errors.append(f"drafts.json: {e}")
    if (d / "international.json").exists():
        try:
            InternationalFile.model_validate_json((d / "international.json").read_bytes())
        except ValueError as e:
            errors.append(f"international.json: {e}")
    return errors


if __name__ == "__main__":
    problems = validate_dir(Path(sys.argv[1] if len(sys.argv) > 1 else "processed"))
    print("\n".join(problems) or "ok")
    sys.exit(1 if problems else 0)

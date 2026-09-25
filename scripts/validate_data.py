#!/usr/bin/env python3
"""Validate processed datasets (schema + referential integrity). Exit code 1 on any problem.

    python scripts/validate_data.py                         # data/processed and the [ЖИШЭЭ] sample
    python scripts/validate_data.py path/to/processed ...
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))

from pipeline.validate import validate_dir  # noqa: E402

DEFAULT = [ROOT / "data" / "processed", ROOT / "contracts" / "fixtures" / "processed"]


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv] or DEFAULT
    failed = False
    for d in dirs:
        if not (d / "laws.jsonl").exists():
            print(f"FAIL {d}: laws.jsonl not found")
            failed = True
            continue
        problems = validate_dir(d)
        print(f"{'FAIL' if problems else 'ok  '} {d.relative_to(ROOT) if d.is_relative_to(ROOT) else d}"
              + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems:
            print("   ", p)
        failed |= bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

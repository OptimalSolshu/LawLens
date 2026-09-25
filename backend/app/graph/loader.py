"""Load data/processed/* (contracts/data-format.md) into Neo4j.

Usage: python -m app.graph.loader ../data/processed
Develop against contracts/fixtures/processed/ until real data lands.
"""
import sys
from pathlib import Path

from .driver import get_driver

SCHEMA = Path(__file__).with_name("schema.cypher")


def apply_schema(session) -> None:
    statements = "\n".join(l for l in SCHEMA.read_text().splitlines() if not l.lstrip().startswith("//"))
    for stmt in filter(None, (s.strip() for s in statements.split(";"))):
        session.run(stmt)


def load(processed_dir: Path) -> None:
    with get_driver().session() as session:
        apply_schema(session)
        # TODO(member 1): MERGE laws/articles, refs, similar, relations, drafts, international, amendments
        raise NotImplementedError("loader")


if __name__ == "__main__":
    load(Path(sys.argv[1] if len(sys.argv) > 1 else "../data/processed"))

#!/usr/bin/env python3
"""Build the offline [ЖИШЭЭ] demo dataset and the endpoint fixtures.

    python scripts/seed_demo.py              # dataset + endpoint fixtures
    python scripts/seed_demo.py --neo4j      # ... and load the dataset into Neo4j (needs NEO4J_* in .env)

1. data/fixtures/sample/laws/*.txt (invented law texts, every provision marked
   [ЖИШЭЭ]) are parsed by the SAME deterministic parser used for real data.
2. Similarity uses the offline demo embedder; relation judgements come from the
   precomputed file data/fixtures/sample/relations.json (model "demo-llm").
3. Output: contracts/fixtures/processed/*  (served by the API when MOCK=1)
   and contracts/fixtures/<endpoint>.json (recorded example responses).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "data"), str(ROOT / "backend")]

from app.ai.embeddings import DemoEmbedder  # noqa: E402
from app.ai.relations import PrecomputedRelationService  # noqa: E402
from app.parser.law_text import parse_law_text, split_front_matter  # noqa: E402
from pipeline.build import BuildInput, build  # noqa: E402
from pipeline.validate import validate_dir  # noqa: E402

SAMPLE = ROOT / "data" / "fixtures" / "sample"
OUT = ROOT / "contracts" / "fixtures" / "processed"


def split_list(v: str) -> list[str]:
    return [x.strip() for x in v.split(";") if x.strip()]


def load_sample_laws() -> list[dict]:
    laws = []
    for f in sorted((SAMPLE / "laws").glob("*.txt")):
        meta, body = split_front_matter(f.read_text(encoding="utf-8"))
        laws.append({
            "law_id": meta["law_id"], "name": meta["name"],
            "former_names": split_list(meta.get("former_names", "")),
            "short_names": split_list(meta.get("short_names", "")),
            "adopted_date": meta.get("adopted_date") or None, "source_url": meta["source_url"],
            "articles": [a.to_dict() for a in parse_law_text(body, meta["law_id"])],
        })
    return laws


def build_dataset() -> None:
    renum = json.loads((SAMPLE / "renumbering.json").read_text(encoding="utf-8"))["laws"]
    inp = BuildInput(
        laws=load_sample_laws(),
        law_names_files=[SAMPLE / "law_names.json"],
        renumbering=renum,
        drafts=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((SAMPLE / "drafts").glob("*.json"))],
        intl_sources=json.loads((ROOT / "data" / "international" / "sources.json").read_text(encoding="utf-8"))["sources"],
        intl_links=json.loads((SAMPLE / "intl_links.json").read_text(encoding="utf-8"))["links"],
        sample=True,
        stub_url="https://example.org/lawlens-sample/laws/unknown",
    )
    out = build(inp, DemoEmbedder(), PrecomputedRelationService(SAMPLE / "relations.json"))
    out.write(OUT)
    print("sample dataset:", out.summary(), "->", OUT.relative_to(ROOT))
    problems = validate_dir(OUT)
    if problems:
        sys.exit("validation failed:\n" + "\n".join(problems))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--neo4j", action="store_true", help="also load the sample dataset into Neo4j")
    ap.add_argument("--no-fixtures", action="store_true", help="skip regenerating endpoint fixtures")
    args = ap.parse_args()
    build_dataset()
    if not args.no_fixtures:
        from app.mock.record import record_fixtures

        for name in record_fixtures(OUT, ROOT / "contracts" / "fixtures"):
            print("  fixture", name)
    if args.neo4j:
        from app.graph.loader import load

        load(OUT, reset=True)


if __name__ == "__main__":
    main()

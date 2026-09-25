#!/usr/bin/env python3
"""Build data/processed/* from REAL sources (contracts/data-format.md).

    python scripts/build_processed_data.py                     # offline: demo embedder, no LLM
    python scripts/build_processed_data.py --embed-model       # BAAI/bge-m3 (needs data/requirements-ml.txt)
    python scripts/build_processed_data.py --llm               # Claude relation judgements (ANTHROPIC_API_KEY)

Inputs
  data/<law_id>.json            parse_law.py output (PDF from legalinfo.mn), one per parsed law
  data/law_names.json           current / former / short names and aliases
  data/raw/drafts/*.json        bills (same shape as data/fixtures/sample/drafts/*.json), if any
  data/international/*.json     curated sources + suggested links
Parsed laws are listed in PARSED below with their legalinfo.mn URL.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "data"), str(ROOT / "backend")]

from app.ai.embeddings import DemoEmbedder, get_embedder  # noqa: E402
from app.ai.relations import get_relation_service  # noqa: E402
from app.parser.names import load_law_names  # noqa: E402
from pipeline.build import BuildInput, build  # noqa: E402
from pipeline.from_lawgraph import convert_law  # noqa: E402
from pipeline.validate import validate_dir  # noqa: E402

PARSED = {
    "labor-2021": ("data/labor-2021.json", "https://legalinfo.mn/mn/detail?lawId=16230709635751"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--embed-model", action="store_true", help="use sentence-transformers (EMBED_MODEL, default BAAI/bge-m3)")
    ap.add_argument("--llm", action="store_true", help="use Claude for relation judgements (cached in data/cache/llm)")
    args = ap.parse_args()

    names = ROOT / "data" / "law_names.json"
    former = {r["current_name"]: r["former_names"] for r in load_law_names(names)}
    laws = []
    for lid, (path, url) in PARSED.items():
        doc = json.loads((ROOT / path).read_text(encoding="utf-8"))
        laws.append(convert_law(doc, url, former).model_dump(exclude={"sample"}))
    drafts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data" / "raw" / "drafts").glob("*.json"))]
    intl_dir = ROOT / "data" / "international"
    inp = BuildInput(
        laws=laws, law_names_files=[names], drafts=drafts,
        intl_sources=json.loads((intl_dir / "sources.json").read_text(encoding="utf-8"))["sources"],
        intl_links=json.loads((intl_dir / "links.json").read_text(encoding="utf-8"))["links"],
    )
    embedder = get_embedder(prefer_real=True) if args.embed_model else DemoEmbedder()
    relations = get_relation_service(cache_dir=ROOT / "data" / "cache" / "llm", use_llm=args.llm)
    out = build(inp, embedder, relations)
    out.write(args.out)
    print(f"real dataset ({embedder.model}): {out.summary()} -> {args.out}")
    problems = validate_dir(args.out)
    if problems:
        sys.exit("validation failed:\n" + "\n".join(problems))


if __name__ == "__main__":
    main()

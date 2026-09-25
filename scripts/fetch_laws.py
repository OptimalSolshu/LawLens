#!/usr/bin/env python3
"""Download every law in data/legalinfo_catalog.json and parse it with parse_law.py.

    python scripts/fetch_laws.py            # saved pages are reused; data/<law_id>.json rewritten
    python scripts/fetch_laws.py --force    # download every page again (picks up new amendments)

legalinfo.mn page -> data/raw/laws/<law_id>.html (not committed) -> data/<law_id>.json
Then `python scripts/build_processed_data.py` turns the parsed laws into data/processed.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "data")]

import parse_law  # noqa: E402
from pipeline.sources import LegalInfoHttpSource  # noqa: E402


def parse(page: Path, law_id: str, name: str) -> dict:
    """Same output as `parse_law.py page.html --id law_id --title name`."""
    law, chapters, sections, articles, provisions, amendments = parse_law.parse_structure(
        parse_law.html_text(page.read_text(encoding="utf-8")), html_input=True)
    law.update(id=law_id, title=name, source_file=page.name)
    terms = parse_law.extract_terms(provisions)
    refs, ext_laws, mentions = parse_law.extract_links(articles, provisions, terms)
    for p in provisions:
        p["modality"] = parse_law.modality(p["text"])
    actors = [{"id": f"actor:{n}", "name": n, "category": c} for n, c, _ in parse_law.ACTORS]
    return {"law": law, "chapters": chapters, "sections": sections, "articles": articles, "provisions": provisions,
            "amendments": amendments, "terms": terms, "actors": actors, "external_laws": ext_laws,
            "references": refs, "mentions": mentions}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="download pages again even if saved")
    args = ap.parse_args()

    src = LegalInfoHttpSource()
    for e in src.entries():
        page = src.out_dir / f"{e['law_id']}.html"
        fresh = args.force or not page.exists()
        src.download(e, force=args.force)
        doc = parse(page, e["law_id"], e["name"])
        out = ROOT / "data" / f"{e['law_id']}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{e['name']:55s} {len(doc['articles']):4d} зүйл {len(doc['provisions']):5d} заалт -> {out.name}")
        if fresh:
            time.sleep(1)  # one page a second; the site is a public government service


if __name__ == "__main__":
    main()

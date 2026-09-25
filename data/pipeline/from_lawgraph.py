"""parse_law.py output (data/<law_id>.json) -> processed/laws.jsonl + refs.jsonl.

Usage (from data/):
    python -m pipeline.from_lawgraph labor-2021.json \
        --source-url labor-2021=https://legalinfo.mn/mn/detail?lawId=16230709635751 -o processed

Several parsed laws can be passed at once; a citation of one parsed law by
another then resolves to its parse_law.py --id. Laws known only by name get
ids.law_id(name). Repealed provisions are left out of `articles`, so
references to them come out as target_missing.
"""
import argparse
import json
from pathlib import Path

from .ids import article_id, law_id
from .schemas import ArticleRec, LawRec, RefRec

LAW_NAMES = Path(__file__).resolve().parents[1] / "law_names.json"
REPEALED = "хүчингүй"


def repealed_ids(d: dict) -> set[str]:
    """Provision/article ids repealed, including everything under a repealed one."""
    gone = {p["id"] for p in d["provisions"] if p["status"] == REPEALED}
    gone |= {a["target"] for a in d["amendments"] if a["type"] == REPEALED}
    changed = True
    while changed:
        extra = {p["id"] for p in d["provisions"] if p["parent"] in gone and p["id"] not in gone}
        gone |= extra
        changed = bool(extra)
    return gone


def to_number(local_id: str) -> str | None:
    """'art49' -> '49', '80.1' -> '80.1'; chapters have no article number."""
    if local_id.startswith("art"):
        return local_id[3:]
    return None if local_id.startswith("ch") else local_id


def convert_law(d: dict, source_url: str, former: dict[str, list[str]]) -> LawRec:
    lid, name = d["law"]["id"], d["law"]["title"]
    gone = repealed_ids(d)
    articles = [ArticleRec(article_id=article_id(lid, str(a["number"])), number=str(a["number"]),
                           parent_number=None, title=a["title"], text=a["text"])
                for a in d["articles"] if a["id"] not in gone]
    art_number = {a["id"]: str(a["number"]) for a in d["articles"]}
    articles += [ArticleRec(article_id=article_id(lid, p["number"]), number=p["number"],
                            parent_number=art_number.get(p["parent"], p["parent"]), title=None, text=p["text"])
                 for p in d["provisions"] if p["id"] not in gone]
    return LawRec(law_id=lid, name=name, former_names=former.get(name, []), short_names=[],
                  adopted_date=d["law"]["adopted"], source_url=source_url, articles=articles)


def convert_refs(d: dict, law: LawRec, resolve: dict[str, tuple[str, str, bool]]) -> list[RefRec]:
    lid = law.law_id
    existing = {a.number for a in law.articles}
    refs = []
    for r in d["references"]:
        num = to_number(r["to"])
        if num is None:  # "энэ хуулийн ... бүлэг": contract has no chapter target
            continue
        missing = num not in existing
        refs.append(RefRec(from_article_id=article_id(lid, r["from"]), to_law_id=lid, to_number=num,
                           to_article_id=None if missing else article_id(lid, num), raw_text=r["raw_text"],
                           matched_name="энэ хууль", uses_old_name=False, target_missing=missing,
                           method="regex", confidence=1.0))
    for e in d["external_laws"]:
        target, matched, old = resolve.get(e["name"], (law_id(e["name"]), e["name"], False))
        for c in e["citations"]:
            refs.append(RefRec(from_article_id=article_id(lid, c["from"]), to_law_id=target, to_number=None,
                               to_article_id=None, raw_text=c["raw_text"], matched_name=matched,
                               uses_old_name=old, target_missing=False, method="regex", confidence=1.0))
    return refs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", type=Path, nargs="+", help="parse_law.py output files")
    ap.add_argument("--source-url", action="append", default=[], metavar="LAW_ID=URL", required=True)
    ap.add_argument("-o", "--out", type=Path, default=Path("processed"))
    args = ap.parse_args()

    urls = dict(s.split("=", 1) for s in args.source_url)
    former = json.loads(LAW_NAMES.read_text(encoding="utf-8"))
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in args.json]
    ids = {d["law"]["title"]: d["law"]["id"] for d in docs}
    # name as cited -> (law_id, matched name, uses_old_name)
    resolve = {cur: (ids.get(cur, law_id(cur)), cur, False) for cur in former}
    resolve |= {old: (ids.get(cur, law_id(cur)), old, True) for cur, olds in former.items() for old in olds}
    resolve |= {name: (lid, name, False) for name, lid in ids.items()}

    laws, refs = [], []
    for d in docs:
        law = convert_law(d, urls[d["law"]["id"]], former)
        laws.append(law)
        refs += convert_refs(d, law, resolve)

    args.out.mkdir(parents=True, exist_ok=True)
    for name, recs in (("laws.jsonl", laws), ("refs.jsonl", refs)):
        (args.out / name).write_text("".join(r.model_dump_json(exclude={"sample"}) + "\n" for r in recs),
                                     encoding="utf-8")
    print(f"{len(laws)} laws, {sum(len(l.articles) for l in laws)} articles, {len(refs)} refs "
          f"({sum(r.target_missing for r in refs)} target_missing, {sum(r.uses_old_name for r in refs)} old name) -> {args.out}")


if __name__ == "__main__":
    main()

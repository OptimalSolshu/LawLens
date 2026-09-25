"""Validate a processed/ directory against contracts/data-format.md.

Usage: python -m pipeline.validate processed

1. schema: every record matches pipeline/schemas.py
2. integrity: unique ids, every article belongs to its law, every reference and
   suggestion points at existing laws / articles / sources (no orphans),
   missing targets are flagged exactly when the cited number does not exist,
   facts have confidence 1.0, suggestions name their model, sources are https.
"""
import json
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
    if not errors:
        errors += integrity(d)
    return errors


def _read(d: Path, name: str) -> list[dict]:
    p = d / name
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def integrity(d: Path) -> list[str]:
    err: list[str] = []
    laws = _read(d, "laws.jsonl")
    law_ids = [l["law_id"] for l in laws]
    if len(law_ids) != len(set(law_ids)):
        err.append("laws.jsonl: duplicate law_id")
    arts: dict[str, dict] = {}
    numbers: dict[str, set[str]] = {}
    sample = any(l.get("_sample") for l in laws)
    for l in laws:
        if not l["source_url"].startswith("https://"):
            err.append(f"law {l['law_id']}: source_url must be https")
        if not l.get("text_available", True) and l["articles"]:
            err.append(f"law {l['law_id']}: name-only law must not have articles")
        numbers[l["law_id"]] = {a["number"] for a in l["articles"]}
        for a in l["articles"]:
            if a["article_id"] in arts:
                err.append(f"duplicate article_id {a['article_id']}")
            if not a["article_id"].startswith(l["law_id"] + ":"):
                err.append(f"article {a['article_id']} does not belong to law {l['law_id']}")
            if a["parent_number"] and a["parent_number"] not in numbers[l["law_id"]] | {x["number"] for x in l["articles"]}:
                err.append(f"article {a['article_id']}: parent {a['parent_number']} not found")
            if sample and a["text"] and not a["text"].startswith("[ЖИШЭЭ]"):
                err.append(f"sample article {a['article_id']} is not labelled [ЖИШЭЭ]")
            arts[a["article_id"]] = a
    texted = {l["law_id"] for l in laws if l.get("text_available", True)}
    for i, r in enumerate(_read(d, "refs.jsonl"), 1):
        where = f"refs.jsonl:{i}"
        if r["from_article_id"] not in arts:
            err.append(f"{where}: from_article_id {r['from_article_id']} does not exist")
        if r["to_law_id"] not in numbers:
            err.append(f"{where}: to_law_id {r['to_law_id']} is not in laws.jsonl")
            continue
        if r["to_article_id"] and r["to_article_id"] not in arts:
            err.append(f"{where}: to_article_id {r['to_article_id']} does not exist")
        if r["to_number"] and r["to_law_id"] in texted:
            exists = r["to_number"] in numbers[r["to_law_id"]]
            if exists == r["target_missing"]:
                err.append(f"{where}: target_missing={r['target_missing']} but provision exists={exists}")
        if r["target_missing"] and r["to_article_id"]:
            err.append(f"{where}: target_missing reference must not have to_article_id")
        if r["method"] == "regex" and r["confidence"] != 1.0:
            err.append(f"{where}: fact (regex) must have confidence 1.0")
    for name, keys in (("similar.jsonl", ("a_article_id", "b_article_id")),
                       ("relations.jsonl", ("a_article_id", "b_article_id")), ("amendments.jsonl", ("article_id",))):
        for i, r in enumerate(_read(d, name), 1):
            if not r.get("model"):
                err.append(f"{name}:{i}: suggestion without model")
            for k in keys:
                if r[k] not in arts:
                    err.append(f"{name}:{i}: orphan {k} {r[k]}")
    intl = json.loads((d / "international.json").read_text(encoding="utf-8")) if (d / "international.json").exists() else {}
    sources = {s["source_id"] for s in intl.get("sources", [])}
    for s in intl.get("sources", []):
        if not s["url"].startswith("https://"):
            err.append(f"international.json: source {s['source_id']} url must be https")
    for ln in intl.get("links", []):
        if ln["article_id"] not in arts or ln["source_id"] not in sources:
            err.append(f"international.json: orphan link {ln['article_id']} -> {ln['source_id']}")
        if not ln.get("model"):
            err.append(f"international.json: link {ln['article_id']} -> {ln['source_id']} without model")
    drafts = json.loads((d / "drafts.json").read_text(encoding="utf-8")) if (d / "drafts.json").exists() else []
    for dr in drafts:
        for lid in [dr["target_law_id"], *dr["cosubmitted_law_ids"]]:
            if lid not in numbers:
                err.append(f"drafts.json: {dr['draft_id']} references unknown law {lid}")
        for aid in dr["amended_article_ids"]:
            if aid not in arts:
                err.append(f"drafts.json: {dr['draft_id']} amends unknown article {aid}")
    return err


if __name__ == "__main__":
    problems = validate_dir(Path(sys.argv[1] if len(sys.argv) > 1 else "processed"))
    print("\n".join(problems) or "ok")
    sys.exit(1 if problems else 0)

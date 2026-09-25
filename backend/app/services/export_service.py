"""CSV export of every major list (UTF-8 with BOM so spreadsheet tools read Cyrillic)."""
import csv
import io

from fastapi import HTTPException

from ..graph.store import GraphStore
from ..schemas import ImpactRequest, LawGroup, RefItem
from . import draft_service, impact_service, international_service, law_service, search_service

COLUMNS = ["law_name", "provision_number", "relationship", "type", "label", "confidence", "flags",
           "source_url", "anchor_number", "explanation", "model", "snippet"]

REL = {
    "incoming": "Үүнийг иш татсан", "outgoing": "Үүнээс иш татсан",
    "former_name_refs": "Хуучин нэр / дугаар", "missing_target_refs": "Заалт олдсонгүй",
    "similar": "Ижил асуудлыг зохицуулсан", "overlaps": "Болзошгүй давхардал", "conflicts": "Болзошгүй зөрчил",
    "international": "Олон улсын эх сурвалж", "depth1": "Шууд нөлөөлөл", "depth2": "Дам нөлөөлөл",
    "depth3": "Дам нөлөөлөл (3)", "new_similar": "Шинэ бичвэртэй төстэй",
    "covered": "Тусгагдсан", "missing": "Орхигдсон", "review": "Шалгах шаардлагатай", "search": "Хайлтын үр дүн",
}
KINDS = ("connections", "law_connections", "impact", "draft_gap", "international", "search")


def label(type_: str, confidence: float) -> str:
    return "Баримт" if type_ == "fact" else f"Санал, {round(confidence * 100)}%"


def _flags(it: RefItem) -> str:
    out = []
    if it.flags.uses_old_name:
        out.append("Хуучин нэр")
    if it.flags.target_missing:
        out.append("Заалт олдсонгүй")
    return "; ".join(out)


def _row(rel: str, it: RefItem) -> dict:
    return {"law_name": it.law_name, "provision_number": it.number or "", "relationship": REL[rel], "type": it.type,
            "label": label(it.type, it.confidence), "confidence": it.confidence, "flags": _flags(it),
            "source_url": it.source_url, "anchor_number": it.anchor_number or "", "explanation": it.explanation or "",
            "model": it.model or "", "snippet": it.snippet}


def _groups(rel: str, groups: list[LawGroup]) -> list[dict]:
    return [_row(rel, it) for g in groups for it in g.items]


def rows(store: GraphStore, kind: str, *, article_id=None, law_id=None, draft_id=None, q=None, list_name=None,
         new_text=None, new_name=None, new_number=None, depth=2) -> list[dict]:
    if kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {', '.join(KINDS)}")
    out: list[dict] = []
    if kind in ("connections", "law_connections"):
        if kind == "connections":
            _need(article_id, "article_id")
            conn = law_service.article_connections(store, article_id)
        else:
            _need(law_id, "law_id")
            conn = law_service.law_connections(store, law_id)
        for name in ("incoming", "outgoing", "former_name_refs", "missing_target_refs"):
            out += _groups(name, getattr(conn, name))
        for name in ("similar", "overlaps", "conflicts"):
            out += [_row(name, it) for it in getattr(conn, name)]
    elif kind == "impact":
        if not (article_id or law_id):
            raise HTTPException(422, "article_id or law_id is required")
        req = ImpactRequest(article_id=article_id if not new_name else None,
                            law_id=law_id or (article_id.split(":")[0] if new_name else None),
                            new_text=new_text, new_name=new_name, new_number=new_number, depth=depth)
        resp = impact_service.compute(store, req)
        for level in resp.depths:
            out += _groups(f"depth{level.depth}", level.groups)
        out += [_row("new_similar", it) for it in resp.new_similar]
    elif kind == "draft_gap":
        _need(draft_id, "draft_id")
        g = draft_service.gap(store, draft_id)
        out += _groups("covered", g.covered) + _groups("missing", g.missing) + _groups("review", g.review)
    elif kind == "international":
        _need(article_id, "article_id")
        intl = international_service.international(store, article_id)
        for it in intl.treaties + intl.foreign_laws:
            out.append({"law_name": it.title, "provision_number": it.provision or "", "relationship": REL["international"],
                        "type": it.type, "label": label(it.type, it.relevance), "confidence": it.relevance,
                        "flags": "", "source_url": it.url, "anchor_number": it.anchor_number or "",
                        "explanation": it.explanation, "model": it.model or "", "snippet": it.summary})
    elif kind == "search":
        _need(q, "q")
        for h in search_service.search(store, q).articles:
            out.append({"law_name": h.law_name, "provision_number": h.number, "relationship": REL["search"],
                        "type": "fact", "label": "Баримт", "confidence": 1.0, "flags": "", "source_url": h.source_url,
                        "anchor_number": "", "explanation": "", "model": "", "snippet": h.snippet})
    if list_name:
        if list_name not in REL:
            raise HTTPException(422, f"unknown list: {list_name}")
        out = [r for r in out if r["relationship"] == REL[list_name]]
    return out


def to_csv(data: list[dict]) -> str:
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\r\n")
    w.writeheader()
    w.writerows(data)
    return buf.getvalue()


def _need(value, name: str) -> None:
    if not value:
        raise HTTPException(422, f"{name} is required")

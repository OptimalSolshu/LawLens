"""Curated international sources, resolution suggestions, side-by-side relation view."""
from fastapi import HTTPException

from ..graph.store import GraphStore
from ..schemas import Amendment, IntlItem, International, RelationDetail, SourceRef
from .law_service import get_article_or_404, selection
from .reference_service import Ctx, article_detail, article_url


def _items(store: GraphStore, sel: dict[str, dict]) -> list[IntlItem]:
    best: dict[str, IntlItem] = {}
    for ln in store.intl_links(list(sel)):
        item = IntlItem(source_id=ln["source_id"], kind=ln["kind"], country_or_org=ln["country_or_org"],
                        title=ln["title"], url=ln["url"], summary=ln["summary"], relevance=ln["relevance"],
                        explanation=ln["explanation"], provision=ln.get("provision"), model=ln.get("model"),
                        anchor_number=sel[ln["article_id"]]["number"])
        if ln["source_id"] not in best or best[ln["source_id"]].relevance < item.relevance:
            best[ln["source_id"]] = item
    return sorted(best.values(), key=lambda i: (-i.relevance, i.source_id))


def international(store: GraphStore, article_id: str) -> International:
    art = get_article_or_404(store, article_id)
    items = _items(store, selection(store, art))
    return International(article_id=article_id, foreign_laws=[i for i in items if i.kind == "foreign_law"],
                         treaties=[i for i in items if i.kind == "treaty"])


def _amendment(store: GraphStore, rec: dict) -> Amendment:
    ctx = Ctx(store)
    sources = store.intl_sources()
    refs = []
    for sid in rec["based_on_source_ids"]:
        if sid in sources:
            s = sources[sid]
            title = f"{s['title']}, {s['provision']}" if s.get("provision") else s["title"]
            refs.append(SourceRef(kind=s["kind"], id=sid, title=title, url=s["url"]))
        elif a := ctx.article(sid):
            law = ctx.law(a["law_id"])
            refs.append(SourceRef(kind="law_article", id=sid, title=f"{law['name']} {a['number']}",
                                  url=article_url(law, a["number"])))
    conf = rec.get("confidence")
    return Amendment(article_id=rec["article_id"], suggested_text=rec["suggested_text"], reason=rec["reason"],
                     sources=refs, confidence=conf if conf is not None else 0.5, model=rec["model"])


def amendment(store: GraphStore, article_id: str) -> Amendment:
    art = get_article_or_404(store, article_id)
    recs = store.amendments(list(selection(store, art)))
    if not recs:
        raise HTTPException(404, f"no amendment suggestion for {article_id}")
    return _amendment(store, recs[0])


def relation_detail(store: GraphStore, a_id: str, b_id: str) -> RelationDetail:
    a, b = get_article_or_404(store, a_id), get_article_or_404(store, b_id)
    pair = {a_id, b_id}
    rel = next((r for r in store.relations([a_id]) if {r["a_article_id"], r["b_article_id"]} == pair), None)
    if not rel:
        raise HTTPException(404, f"no relation suggestion between {a_id} and {b_id}")
    score = next((s["score"] for s in store.similar([a_id]) if {s["a_article_id"], s["b_article_id"]} == pair), None)
    recs = [r for r in store.amendments([a_id, b_id]) if pair & set(r["based_on_source_ids"])] or store.amendments([a_id, b_id])
    ctx = Ctx(store)
    intl = {i.source_id: i for i in _items(store, {a_id: a, b_id: b})}
    return RelationDetail(a=article_detail(ctx, a), b=article_detail(ctx, b), kind=rel["kind"],
                          confidence=rel["confidence"], explanation=rel["explanation"], model=rel["model"],
                          score=score, international=list(intl.values()),
                          resolution=_amendment(store, recs[0]) if recs else None)

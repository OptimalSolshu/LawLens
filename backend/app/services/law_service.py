"""Laws, articles and connection lists (law level and provision level)."""
from fastapi import HTTPException

from ..graph.store import GraphStore, under
from ..parser.normalize import norm
from ..schemas import (Article, ArticleConnections, ConnectionTotals, Connections, Law, LawDetail,
                       LawGroup, LawSummary)
from .reference_service import Ctx, article_detail, count, group, incoming_item, law_summary, outgoing_item
from .similarity_service import relation_items, similar_items


def list_laws(store: GraphStore, q: str = "") -> list[LawSummary]:
    laws = sorted(store.laws(), key=lambda l: (not l.get("text_available", True), -l.get("article_count", 0), l["name"]))
    needle = norm(q)
    if needle:
        laws = [l for l in laws if any(needle in norm(n) for n in [l["name"], *l.get("former_names", []),
                                                                     *l.get("short_names", [])])]
    return [law_summary(l) for l in laws]


def get_law_or_404(store: GraphStore, law_id: str) -> dict:
    law = store.law(law_id)
    if not law:
        raise HTTPException(404, f"law not found: {law_id}")
    return law


def get_law(store: GraphStore, law_id: str) -> LawDetail:
    law = get_law_or_404(store, law_id)
    return LawDetail(
        law=Law(law_id=law["law_id"], name=law["name"], former_names=law.get("former_names", []),
                short_names=law.get("short_names", []), adopted_date=law.get("adopted_date"),
                source_url=law["source_url"], text_available=law.get("text_available", True)),
        articles=list_articles(store, law_id))


def list_articles(store: GraphStore, law_id: str) -> list[Article]:
    get_law_or_404(store, law_id)
    return [Article(article_id=a["article_id"], number=a["number"], title=a.get("title"), text=a.get("text") or "",
                    parent_number=a.get("parent_number")) for a in store.articles(law_id)]


def get_article_or_404(store: GraphStore, article_id: str) -> dict:
    a = store.article(article_id)
    if not a:
        raise HTTPException(404, f"article not found: {article_id}")
    return a


def selection(store: GraphStore, article: dict) -> dict[str, dict]:
    """The provision and everything under it (selecting "80 дугаар зүйл" covers 80.1, 80.1.2 ...)."""
    return {a["article_id"]: a for a in store.articles(article["law_id"]) if under(a["number"], article["number"])}


def _connections(ctx: Ctx, sel: dict[str, dict], incoming_refs: list[dict], outgoing_refs: list[dict]) -> Connections:
    ctx.prefetch([r["from_article_id"] for r in incoming_refs] + [r["to_article_id"] for r in outgoing_refs])
    incoming = [incoming_item(ctx, r) for r in incoming_refs]
    outgoing = [outgoing_item(ctx, r) for r in outgoing_refs]
    both = incoming + outgoing
    old = group([i for i in both if i.flags.uses_old_name])
    missing = group([i for i in both if i.flags.target_missing])
    sim = similar_items(ctx, sel)
    rel = relation_items(ctx, sel)
    inc_g, out_g = group(incoming), group(outgoing)
    return Connections(
        incoming=inc_g, outgoing=out_g, former_name_refs=old, missing_target_refs=missing,
        similar=sim, conflicts=rel["conflict"], overlaps=rel["overlap"],
        totals=ConnectionTotals(incoming=count(inc_g), outgoing=count(out_g), former_name_refs=count(old),
                                missing_target_refs=count(missing), similar=len(sim),
                                conflicts=len(rel["conflict"]), overlaps=len(rel["overlap"])))


def article_connections(store: GraphStore, article_id: str) -> ArticleConnections:
    ctx = Ctx(store)
    art = get_article_or_404(store, article_id)
    sel = selection(store, art)
    ctx.prefetch(list(sel))
    ids = list(sel)
    incoming = [r for r in store.refs_to(art["law_id"], ids, [art["number"]], False) if r["from_article_id"] not in sel]
    outgoing = [r for r in store.refs_from(ids) if r["to_article_id"] not in sel]
    conn = _connections(ctx, sel, incoming, outgoing)
    return ArticleConnections(**conn.model_dump(), article=article_detail(ctx, art))


def law_connections(store: GraphStore, law_id: str) -> Connections:
    ctx = Ctx(store)
    get_law_or_404(store, law_id)
    sel = {a["article_id"]: a for a in store.articles(law_id)}
    ids = list(sel)
    incoming = [r for r in store.refs_to(law_id, ids, None, True) if r["from_law_id"] != law_id]
    outgoing = [r for r in store.refs_from(ids) if r["to_law_id"] != law_id]
    return _connections(ctx, sel, incoming, outgoing)


def groups_total(groups: list[LawGroup]) -> int:
    return count(groups)

"""Similar provisions and overlap / conflict suggestions (type="suggestion")."""
from ..ai.embeddings import DemoEmbedder, cosine, is_demo, min_score
from ..graph.store import GraphStore
from ..schemas import RefItem
from .reference_service import Ctx, article_url, excerpt

_embedder = DemoEmbedder()


def similar_explanation(model: str) -> str:
    label = "Демо similarity (тэмдэгтийн n-gram)" if is_demo(model) else f"Embedding загвар: {model}"
    return f"Шууд иш татаагүй боловч ижил асуудлыг зохицуулсан байж болзошгүй. {label}. Шалгах шаардлагатай."


def _item(ctx: Ctx, other_id: str, anchor_number: str | None, confidence: float, model: str,
          explanation: str, score: float | None) -> RefItem | None:
    other = ctx.article(other_id)
    if not other:
        return None
    law = ctx.law(other["law_id"])
    return RefItem(law_id=law["law_id"], law_name=law["name"], article_id=other_id, number=other["number"],
                   snippet=excerpt(other.get("text")), source_url=article_url(law, other["number"]),
                   type="suggestion", confidence=round(confidence, 3), anchor_number=anchor_number,
                   score=score, explanation=explanation, model=model)


def similar_items(ctx: Ctx, sel: dict[str, dict]) -> list[RefItem]:
    recs = [r for r in ctx.store.similar(list(sel)) if not (r["a_article_id"] in sel and r["b_article_id"] in sel)]
    ctx.prefetch([r["a_article_id"] for r in recs] + [r["b_article_id"] for r in recs])
    out = []
    for r in recs:
        mine, other = (r["a_article_id"], r["b_article_id"]) if r["a_article_id"] in sel else (r["b_article_id"], r["a_article_id"])
        it = _item(ctx, other, sel[mine]["number"], r["score"], r["model"], similar_explanation(r["model"]), r["score"])
        if it:
            out.append(it)
    return sorted(out, key=lambda i: (-(i.score or 0), i.article_id))


def relation_items(ctx: Ctx, sel: dict[str, dict]) -> dict[str, list[RefItem]]:
    """{"conflict": [...], "overlap": [...]} — "consistent" judgements are not listed."""
    sims = {frozenset((r["a_article_id"], r["b_article_id"])): r["score"] for r in ctx.store.similar(list(sel))}
    recs = [r for r in ctx.store.relations(list(sel)) if not (r["a_article_id"] in sel and r["b_article_id"] in sel)]
    ctx.prefetch([r["a_article_id"] for r in recs] + [r["b_article_id"] for r in recs])
    out: dict[str, list[RefItem]] = {"conflict": [], "overlap": []}
    for r in recs:
        if r["kind"] not in out:
            continue
        mine, other = (r["a_article_id"], r["b_article_id"]) if r["a_article_id"] in sel else (r["b_article_id"], r["a_article_id"])
        it = _item(ctx, other, sel[mine]["number"], r["confidence"], r["model"], r["explanation"],
                   sims.get(frozenset((mine, other))))
        if it:
            out[r["kind"]].append(it)
    for k in out:
        out[k].sort(key=lambda i: (-i.confidence, i.article_id))
    return out


def similar_to_text(ctx: Ctx, text: str, exclude_law: str, anchor_number: str | None, limit: int = 10) -> list[RefItem]:
    """Runtime suggestion for impact analysis: provisions of OTHER laws similar to a draft text."""
    if not text.strip():
        return []
    candidates = [a for a in ctx.store.all_articles() if a["law_id"] != exclude_law and a.get("text")]
    if not candidates:
        return []
    vecs = _embedder.embed([text] + [a["text"] for a in candidates])
    q, rest = vecs[0], vecs[1:]
    scored = sorted(((cosine(q, v), a) for v, a in zip(rest, candidates)), key=lambda x: -x[0])
    out = []
    for score, a in scored[:limit]:
        if score < min_score(_embedder.model):
            break
        ctx.prefetch([a["article_id"]])
        it = _item(ctx, a["article_id"], anchor_number, min(score, 1.0), _embedder.model,
                   similar_explanation(_embedder.model), round(min(score, 1.0), 3))
        if it:
            out.append(it)
    return out

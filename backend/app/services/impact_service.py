"""Hypothetical impact analysis. Nothing is written to the graph.

Depth 1: provisions that cite the changed provision (or an article / part
containing it). Depth n: provisions that cite a depth n-1 provision (or its
containing article / part). A provision is listed once, at its smallest depth.

Change kinds
  text     (article_id [+ new_text])  seeds = the provision; citations of it
                                      and of its containing article/part count
  renumber (article_id + new_number)  seeds = the provision and everything under
                                      it; every citation would point at a number
                                      that no longer exists (flags.target_missing)
  rename   (law_id + new_name)        seeds = the whole law; every citation by
                                      name from other laws would use an old name
                                      (flags.uses_old_name)
  none     (law_id only)              seeds = the whole law
"""
from ..graph.store import GraphStore, number_key
from ..parser.ids import ancestors, article_id as make_article_id
from ..schemas import (Flags, ImpactChange, ImpactDepth, ImpactRequest, ImpactResponse, ImpactTotals, LawGroup,
                       RefItem)
from .law_service import get_article_or_404, get_law_or_404, selection
from .reference_service import SELF_NAMES, Ctx, count, genitive, group, incoming_item
from .similarity_service import similar_to_text


def _with_ancestors(law_id_: str, number: str) -> list[str]:
    return [make_article_id(law_id_, n) for n in [number, *ancestors(number)]]


def compute(store: GraphStore, req: ImpactRequest) -> ImpactResponse:
    ctx = Ctx(store)
    if req.article_id:
        art = get_article_or_404(store, req.article_id)
        law = ctx.law(art["law_id"])
    else:
        art = None
        law = get_law_or_404(store, req.law_id)
    law_id = law["law_id"]

    # ---- depth 1 --------------------------------------------------------------
    if req.new_name:
        kind = "rename"
        ids = [a["article_id"] for a in store.articles(law_id)]
        refs = [r for r in store.refs_to(law_id, ids, None, True)
                if r["from_law_id"] != law_id and r["matched_name"] not in SELF_NAMES]
        seeds = set(ids)
        summary = f"«{law['name']}»-ийн нэрийг «{req.new_name}» болгох"
    elif art and req.new_number:
        kind = "renumber"
        sel = selection(store, art)
        seeds = set(sel)
        refs = [r for r in store.refs_to(law_id, list(sel), [], False) if r["from_article_id"] not in seeds]
        summary = f"{genitive(law['name'])} {art['number']} заалтын дугаарыг {req.new_number} болгох"
    elif art:
        kind = "text" if req.new_text else "none"
        seeds = {art["article_id"]}
        # citations of the provision itself and of the article/part that contains it
        refs = [r for r in store.refs_to(law_id, _with_ancestors(law_id, art["number"]), [], False)
                if r["from_article_id"] not in seeds]
        summary = (f"{genitive(law['name'])} {art['number']} заалтын бичвэрийг өөрчлөх" if req.new_text
                   else f"{genitive(law['name'])} {art['number']} заалтаас хамаарах заалтууд")
    else:
        kind = "none"
        ids = [a["article_id"] for a in store.articles(law_id)]
        seeds = set(ids)
        refs = [r for r in store.refs_to(law_id, ids, None, True) if r["from_law_id"] != law_id]
        summary = f"«{law['name']}»-д өөрчлөлт оруулах"

    seen: set[str] = set(seeds)
    depths: list[list[RefItem]] = []
    frontier: dict[str, dict] = {}
    items: list[RefItem] = []
    ctx.prefetch([r["from_article_id"] for r in refs])
    for r in sorted(refs, key=lambda r: (r["from_article_id"], number_key(r["to_number"]))):
        if r["from_article_id"] in seen:
            continue
        seen.add(r["from_article_id"])
        flags = Flags(uses_old_name=kind == "rename" or bool(r["uses_old_name"]),
                      target_missing=kind == "renumber" or bool(r["target_missing"]))
        via = "шууд иш татсан" if r["to_article_id"] in seeds or kind in ("rename", "none") else "агуулсан зүйл/хэсгийг иш татсан"
        reason = f"{r['to_number'] or 'хуулийг бүхэлд нь'}: {via}."
        if kind == "rename":
            reason += " Нэр өөрчлөгдвөл энэ ишлэл хуучин нэртэй болно."
        if kind == "renumber":
            reason += f" Дугаар {req.new_number} болбол энэ ишлэл олдохгүй заалт руу заана."
        items.append(incoming_item(ctx, r, explanation=reason, flags=flags))
        frontier[r["from_article_id"]] = r
    depths.append(items)

    # ---- depth 2..n -------------------------------------------------------------
    for _ in range(2, req.depth + 1):
        nxt: dict[str, dict] = {}
        level: list[RefItem] = []
        by_target: dict[str, list[dict]] = {}
        for aid, via_ref in frontier.items():
            lid, num = via_ref["from_law_id"], via_ref["from_number"]
            for r in store.refs_to(lid, _with_ancestors(lid, num), [], False):
                by_target.setdefault(r["from_article_id"], []).append((r, via_ref))
        ctx.prefetch(list(by_target))
        for from_id in sorted(by_target):
            if from_id in seen:
                continue
            seen.add(from_id)
            r, via = min(by_target[from_id], key=lambda rv: (number_key(rv[0]["to_number"]), rv[1]["from_article_id"]))
            via_law = ctx.law(via["from_law_id"])["name"]
            reason = f"{genitive(via_law)} {via['from_number']}-ээр дамжсан: {r['to_number']}-ийг иш татсан."
            level.append(incoming_item(ctx, r, explanation=reason))
            nxt[from_id] = r
        depths.append(level)
        frontier = nxt
        if not frontier:
            break
    while len(depths) < req.depth:
        depths.append([])

    groups = [group(level) for level in depths]
    new_similar = similar_to_text(ctx, req.new_text, law_id, art["number"] if art else None) if req.new_text else []
    affected_laws = {g.law_id for gs in groups for g in gs}
    return ImpactResponse(
        depths=[ImpactDepth(depth=i + 1, groups=g, count=count(g)) for i, g in enumerate(groups)],
        new_similar=new_similar,
        totals=ImpactTotals(laws=len(affected_laws), articles=sum(count(g) for g in groups),
                            new_similar=len(new_similar), direct=count(groups[0]),
                            indirect=sum(count(g) for g in groups[1:])),
        direct_impact=groups[0],
        indirect_impact=[g for gs in groups[1:] for g in gs],
        change=ImpactChange(kind=kind, law_id=law_id, law_name=law["name"], article_id=art["article_id"] if art else None,
                            number=art["number"] if art else None, summary=summary),
    )


def for_article(store: GraphStore, article_id: str, *, new_text=None, new_name=None, new_number=None, depth=2):
    if new_name:
        art = get_article_or_404(store, article_id)
        return compute(store, ImpactRequest(law_id=art["law_id"], new_name=new_name, depth=depth))
    return compute(store, ImpactRequest(article_id=article_id, new_text=new_text, new_number=new_number, depth=depth))


def flatten(groups: list[LawGroup]) -> list[RefItem]:
    return [i for g in groups for i in g.items]

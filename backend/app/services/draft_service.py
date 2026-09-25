"""Bills and the co-submitted amendment gap.

A law is EXPECTED to be amended when one of its provisions cites a provision
the bill amends (or the law the bill renames). Expected laws in the bill's
package are "Тусгагдсан" (covered); the rest are "Орхигдсон" (missing).
Laws reached only indirectly (depth 2) are listed as "Шалгах шаардлагатай".
This is a checking aid computed from citations, not a legal requirement.
"""
from fastapi import HTTPException

from ..graph.store import GraphStore
from ..schemas import (AmendedProvision, Draft, DraftDetail, DraftGap, DraftOp, ImpactRequest, RefItem)
from .impact_service import compute, flatten
from .reference_service import Ctx, article_detail, group, law_summary


def list_drafts(store: GraphStore) -> list[Draft]:
    return [Draft(**d) for d in sorted(store.drafts(), key=lambda d: d["draft_id"])]


def get_draft_or_404(store: GraphStore, draft_id: str) -> dict:
    d = store.draft(draft_id)
    if not d:
        raise HTTPException(404, f"draft not found: {draft_id}")
    return d


def _impacts(store: GraphStore, d: dict) -> tuple[list[RefItem], list[RefItem]]:
    if d.get("new_name"):
        reqs = [ImpactRequest(law_id=d["target_law_id"], new_name=d["new_name"], depth=2)]
    elif d["amended_article_ids"]:
        reqs = [ImpactRequest(article_id=a, depth=2) for a in d["amended_article_ids"] if store.article(a)]
    else:
        reqs = [ImpactRequest(law_id=d["target_law_id"], depth=2)]
    direct: dict[str, RefItem] = {}
    indirect: dict[str, RefItem] = {}
    for req in reqs:
        resp = compute(store, req)
        for it in flatten(resp.depths[0].groups):
            direct.setdefault(it.article_id, it)
        for level in resp.depths[1:]:
            for it in flatten(level.groups):
                indirect.setdefault(it.article_id, it)
    indirect = {k: v for k, v in indirect.items() if k not in direct}
    return list(direct.values()), list(indirect.values())


def gap(store: GraphStore, draft_id: str) -> DraftGap:
    d = get_draft_or_404(store, draft_id)
    target, cos = d["target_law_id"], set(d["cosubmitted_law_ids"])
    direct, indirect = _impacts(store, d)
    direct = [i for i in direct if i.law_id != target]
    direct_laws = {i.law_id for i in direct}
    covered = group([i for i in direct if i.law_id in cos])
    missing = group([i for i in direct if i.law_id not in cos])
    review = group([i for i in indirect if i.law_id != target and i.law_id not in direct_laws and i.law_id not in cos])
    return DraftGap(draft_id=draft_id, found=len(covered) + len(missing), covered=covered, missing=missing,
                    review=review)


def detail(store: GraphStore, draft_id: str) -> DraftDetail:
    d = get_draft_or_404(store, draft_id)
    ctx = Ctx(store)
    ops = [DraftOp(**o) for o in d.get("operations", [])]
    ctx.prefetch([o.article_id for o in ops])
    amended = [AmendedProvision(op=o, article=article_detail(ctx, a) if (a := ctx.article(o.article_id)) else None)
               for o in ops]
    return DraftDetail(draft=Draft(**d), target_law=law_summary(ctx.law(d["target_law_id"])), amended=amended,
                       cosubmitted=[law_summary(ctx.law(x)) for x in d["cosubmitted_law_ids"]],
                       gap=gap(store, draft_id))

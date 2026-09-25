"""Turn graph records into cited API items (RefItem / LawGroup / ArticleDetail).

Every item carries law name, provision number, source URL, type and
confidence (CLAUDE.md §7). Wording is descriptive: it states what the text
says and what needs checking, never a legal verdict.
"""
from collections import defaultdict

from ..graph.store import GraphStore, number_key
from ..schemas import ArticleDetail, Flags, LawGroup, LawSummary, RefItem

SNIPPET = 420
SELF_NAMES = {"энэ хууль", "энэ зүйл"}


def excerpt(text: str | None, n: int = SNIPPET) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def genitive(law_name: str) -> str:
    return law_name[:-5] + "хуулийн" if law_name.endswith("хууль") else law_name


def article_url(law: dict, number: str | None) -> str:
    if number and law.get("text_available", True):
        return f"{law['source_url']}#{number}"
    return law["source_url"]


class Ctx:
    """Per-request lookup cache over a GraphStore."""

    def __init__(self, store: GraphStore):
        self.store = store
        self._laws = {l["law_id"]: l for l in store.laws()}
        self._arts: dict[str, dict] = {}

    def law(self, law_id: str) -> dict:
        return self._laws.get(law_id) or {"law_id": law_id, "name": law_id, "former_names": [], "short_names": [],
                                          "source_url": "https://legalinfo.mn/mn", "text_available": False,
                                          "article_count": 0, "adopted_date": None}

    def laws(self) -> list[dict]:
        return list(self._laws.values())

    def prefetch(self, ids) -> None:
        missing = [i for i in set(ids) if i and i not in self._arts]
        if missing:
            self._arts.update(self.store.articles_by_id(missing))

    def article(self, article_id: str | None) -> dict | None:
        if not article_id:
            return None
        if article_id not in self._arts:
            self.prefetch([article_id])
        return self._arts.get(article_id)


def law_summary(law: dict) -> LawSummary:
    return LawSummary(law_id=law["law_id"], name=law["name"], former_names=law.get("former_names", []),
                      article_count=law.get("article_count", 0), short_names=law.get("short_names", []),
                      text_available=law.get("text_available", True), source_url=law.get("source_url"))


def article_detail(ctx: Ctx, a: dict) -> ArticleDetail:
    law = ctx.law(a["law_id"])
    return ArticleDetail(article_id=a["article_id"], number=a["number"], title=a.get("title"), text=a.get("text") or "",
                         parent_number=a.get("parent_number"), law_id=law["law_id"], law_name=law["name"],
                         source_url=article_url(law, a["number"]))


def describe_ref(ctx: Ctx, r: dict) -> str | None:
    parts = []
    target = ctx.law(r["to_law_id"])
    if r.get("uses_old_name"):
        parts.append(f"Хуучин нэрээр («{r['matched_name']}») иш татсан. Одоогийн нэр: «{target['name']}».")
    if r.get("target_missing"):
        parts.append(f"{genitive(target['name'])} одоогийн бичвэрт {r['to_number']} дугаартай заалт олдсонгүй.")
        if r.get("current_number"):
            parts.append(f"Харьцуулсан хүснэгтээр одоогийн дугаар: {r['current_number']}.")
    return " ".join(parts) or None


def ref_type(r: dict) -> str:
    return "fact" if r.get("method") == "regex" else "suggestion"


def _flags(r: dict) -> Flags:
    return Flags(uses_old_name=bool(r.get("uses_old_name")), target_missing=bool(r.get("target_missing")))


def incoming_item(ctx: Ctx, r: dict, explanation: str | None = None, flags: Flags | None = None) -> RefItem:
    """The citing provision (from side) as seen from the cited selection."""
    law = ctx.law(r["from_law_id"])
    src = ctx.article(r["from_article_id"])
    return RefItem(
        law_id=law["law_id"], law_name=law["name"], article_id=r["from_article_id"], number=r["from_number"],
        snippet=excerpt(src["text"] if src and src.get("text") else r["raw_text"]),
        source_url=article_url(law, r["from_number"]), type=ref_type(r), confidence=r["confidence"],
        flags=flags or _flags(r), anchor_number=r["to_number"],
        explanation=explanation if explanation is not None else describe_ref(ctx, r),
        raw_text=r["raw_text"], matched_name=r["matched_name"], current_number=r.get("current_number"),
        model=None if r.get("method") == "regex" else r.get("method"), cited_number=r["to_number"],
    )


def outgoing_item(ctx: Ctx, r: dict) -> RefItem:
    """The cited provision (to side) as seen from the citing selection."""
    law = ctx.law(r["to_law_id"])
    target = ctx.article(r["to_article_id"])
    return RefItem(
        law_id=law["law_id"], law_name=law["name"], article_id=r["to_article_id"], number=r["to_number"],
        snippet=excerpt(target["text"] if target and target.get("text") else r["raw_text"]),
        source_url=article_url(law, r["to_number"]), type=ref_type(r), confidence=r["confidence"],
        flags=_flags(r), anchor_number=r["from_number"], explanation=describe_ref(ctx, r),
        raw_text=r["raw_text"], matched_name=r["matched_name"], current_number=r.get("current_number"),
        model=None if r.get("method") == "regex" else r.get("method"), cited_number=r["to_number"],
    )


def group(items: list[RefItem]) -> list[LawGroup]:
    by_law: dict[str, list[RefItem]] = defaultdict(list)
    for it in items:
        by_law[it.law_id].append(it)
    groups = [LawGroup(law_id=k, law_name=v[0].law_name, count=len(v),
                       items=sorted(v, key=lambda i: (number_key(i.number), number_key(i.anchor_number))))
              for k, v in by_law.items()]
    return sorted(groups, key=lambda g: (-g.count, g.law_name))


def count(groups: list[LawGroup]) -> int:
    return sum(g.count for g in groups)

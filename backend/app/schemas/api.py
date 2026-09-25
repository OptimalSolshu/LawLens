"""API models. Source of truth for contracts/api.md; mirrored by web/src/types.ts.

Every model forbids unknown fields so a drifting fixture fails
tests/test_contracts.py.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Confidence = Annotated[float, Field(ge=0, le=1)]
ItemType = Literal["fact", "suggestion"]

IMPACT_NOTE = "Энэ нь түр тооцоолол бөгөөд хуульд өөрчлөлт оруулахгүй."


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- common -----------------------------------------------------------------

class Flags(Model):
    uses_old_name: bool = False
    target_missing: bool = False


class RefItem(Model):
    """Always describes the OTHER provision; anchor_number is the selected side."""
    law_id: str
    law_name: str
    article_id: str | None
    number: str | None
    snippet: str
    source_url: str
    type: ItemType
    confidence: Confidence
    flags: Flags = Flags()
    anchor_number: str | None = None
    score: float | None = None
    explanation: str | None = None
    # additive (v0.2): evidence for old-name / old-number review and model provenance
    raw_text: str | None = None
    matched_name: str | None = None
    current_number: str | None = None
    model: str | None = None
    cited_number: str | None = None  # the provision number exactly as cited in the text


class LawGroup(Model):
    law_id: str
    law_name: str
    count: int
    items: list[RefItem]

    @model_validator(mode="after")
    def _count_matches(self):
        if self.count != len(self.items):
            raise ValueError(f"count={self.count} but {len(self.items)} items")
        return self


# ---- laws -------------------------------------------------------------------

class Health(Model):
    status: Literal["ok"]
    mock: bool
    dataset: Literal["sample", "real"] = "sample"
    graph: Literal["memory", "neo4j"] = "memory"


class LawSummary(Model):
    law_id: str
    name: str
    former_names: list[str]
    article_count: int
    short_names: list[str] = []
    text_available: bool = True
    source_url: str | None = None


class Law(Model):
    law_id: str
    name: str
    former_names: list[str]
    short_names: list[str]
    adopted_date: str | None
    source_url: str
    text_available: bool = True


class Article(Model):
    article_id: str
    number: str
    title: str | None
    text: str
    parent_number: str | None = None


class LawDetail(Model):
    law: Law
    articles: list[Article]


class ArticleDetail(Article):
    law_id: str
    law_name: str
    source_url: str


# ---- connections ------------------------------------------------------------

class ConnectionTotals(Model):
    incoming: int
    outgoing: int
    former_name_refs: int
    missing_target_refs: int
    similar: int
    conflicts: int
    overlaps: int = 0


class Connections(Model):
    incoming: list[LawGroup]
    outgoing: list[LawGroup]
    former_name_refs: list[LawGroup]
    missing_target_refs: list[LawGroup]
    similar: list[RefItem]
    conflicts: list[RefItem]
    totals: ConnectionTotals
    overlaps: list[RefItem] = []


class ArticleConnections(Connections):
    article: ArticleDetail


# ---- impact -----------------------------------------------------------------

class ImpactRequest(Model):
    law_id: str | None = None
    article_id: str | None = None
    new_text: str | None = Field(default=None, max_length=20000)
    new_name: str | None = Field(default=None, max_length=300)
    new_number: str | None = Field(default=None, pattern=r"^\d+(\.\d+)*$")
    depth: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def _needs_target(self):
        if not (self.law_id or self.article_id):
            raise ValueError("law_id or article_id is required")
        return self


class ArticleImpactRequest(Model):
    """Body of POST /api/articles/{article_id}/impact."""
    new_text: str | None = Field(default=None, max_length=20000)
    new_name: str | None = Field(default=None, max_length=300)
    new_number: str | None = Field(default=None, pattern=r"^\d+(\.\d+)*$")
    depth: int = Field(default=2, ge=1, le=3)


class ImpactDepth(Model):
    depth: int = Field(ge=1, le=3)
    groups: list[LawGroup]
    count: int


class ImpactTotals(Model):
    laws: int
    articles: int
    new_similar: int
    direct: int = 0
    indirect: int = 0


class ImpactChange(Model):
    kind: Literal["text", "rename", "renumber", "none"]
    law_id: str
    law_name: str
    article_id: str | None
    number: str | None
    summary: str


class ImpactResponse(Model):
    depths: list[ImpactDepth]
    new_similar: list[RefItem]
    totals: ImpactTotals
    direct_impact: list[LawGroup] = []
    indirect_impact: list[LawGroup] = []
    change: ImpactChange | None = None
    note: str = IMPACT_NOTE


# ---- drafts -----------------------------------------------------------------

class DraftOp(Model):
    op: Literal["replace", "insert", "delete", "repeal", "add", "rename"]
    law_id: str
    number: str | None
    article_id: str | None
    old_text: str | None
    new_text: str | None
    raw_text: str
    uses_old_name: bool
    target_missing: bool


class Draft(Model):
    draft_id: str
    lawforum_id: str
    title: str
    target_law_id: str
    new_name: str | None
    amended_article_ids: list[str]
    cosubmitted_law_ids: list[str]
    source_url: str
    operations: list[DraftOp] = []
    cosubmitted_titles: list[str] = []


class DraftGap(Model):
    draft_id: str
    found: int
    covered: list[LawGroup]
    missing: list[LawGroup]
    review: list[LawGroup] = []  # reached only indirectly (depth 2): "Шалгах шаардлагатай"


class AmendedProvision(Model):
    op: DraftOp
    article: ArticleDetail | None


class DraftDetail(Model):
    draft: Draft
    target_law: LawSummary
    amended: list[AmendedProvision]
    cosubmitted: list[LawSummary]
    gap: DraftGap


# ---- international / amendment ---------------------------------------------

class IntlItem(Model):
    source_id: str
    kind: Literal["foreign_law", "treaty"]
    country_or_org: str
    title: str
    url: str
    summary: str
    relevance: Confidence
    explanation: str
    type: Literal["suggestion"] = "suggestion"
    provision: str | None = None
    model: str | None = None
    anchor_number: str | None = None


class International(Model):
    article_id: str
    foreign_laws: list[IntlItem]
    treaties: list[IntlItem]


class SourceRef(Model):
    kind: Literal["law_article", "foreign_law", "treaty"]
    id: str
    title: str
    url: str


class Amendment(Model):
    article_id: str
    suggested_text: str
    reason: str
    sources: list[SourceRef]
    type: Literal["suggestion"] = "suggestion"
    confidence: Confidence
    model: str


class RelationDetail(Model):
    """Side-by-side view of a suggested overlap / conflict."""
    a: ArticleDetail
    b: ArticleDetail
    kind: Literal["conflict", "overlap", "consistent"]
    type: Literal["suggestion"] = "suggestion"
    confidence: Confidence
    explanation: str
    model: str
    score: float | None
    international: list[IntlItem]
    resolution: Amendment | None


# ---- search -----------------------------------------------------------------

class ArticleHit(Model):
    article_id: str
    law_id: str
    law_name: str
    number: str
    title: str | None
    snippet: str
    source_url: str


class SearchResponse(Model):
    query: str
    laws: list[LawSummary]
    articles: list[ArticleHit]

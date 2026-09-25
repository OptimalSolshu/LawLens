"""API models. Source of truth for contracts/api.md; mirrored by web/src/types.ts.

Every model forbids unknown fields so a drifting fixture fails
tests/test_contracts.py.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Confidence = Annotated[float, Field(ge=0, le=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- common -----------------------------------------------------------------

class Flags(Model):
    uses_old_name: bool = False
    target_missing: bool = False


class RefItem(Model):
    law_id: str
    law_name: str
    article_id: str | None
    number: str | None
    snippet: str
    source_url: str
    type: Literal["fact", "suggestion"]
    confidence: Confidence
    flags: Flags = Flags()
    anchor_number: str | None = None
    score: float | None = None
    explanation: str | None = None


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


class LawSummary(Model):
    law_id: str
    name: str
    former_names: list[str]
    article_count: int


class Law(Model):
    law_id: str
    name: str
    former_names: list[str]
    short_names: list[str]
    adopted_date: str | None
    source_url: str


class Article(Model):
    article_id: str
    number: str
    title: str | None
    text: str


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


class Connections(Model):
    incoming: list[LawGroup]
    outgoing: list[LawGroup]
    former_name_refs: list[LawGroup]
    missing_target_refs: list[LawGroup]
    similar: list[RefItem]
    conflicts: list[RefItem]
    totals: ConnectionTotals


class ArticleConnections(Connections):
    article: ArticleDetail


# ---- impact -----------------------------------------------------------------

class ImpactRequest(Model):
    law_id: str | None = None
    article_id: str | None = None
    new_text: str | None = None
    new_name: str | None = None
    depth: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def _needs_target(self):
        if not (self.law_id or self.article_id):
            raise ValueError("law_id or article_id is required")
        return self


class ImpactDepth(Model):
    depth: int = Field(ge=1, le=3)
    groups: list[LawGroup]
    count: int


class ImpactTotals(Model):
    laws: int
    articles: int
    new_similar: int


class ImpactResponse(Model):
    depths: list[ImpactDepth]
    new_similar: list[RefItem]
    totals: ImpactTotals


# ---- drafts -----------------------------------------------------------------

class Draft(Model):
    draft_id: str
    lawforum_id: str
    title: str
    target_law_id: str
    new_name: str | None
    amended_article_ids: list[str]
    cosubmitted_law_ids: list[str]
    source_url: str


class DraftGap(Model):
    draft_id: str
    found: int
    covered: list[LawGroup]
    missing: list[LawGroup]


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

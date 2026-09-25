"""Pydantic models for data/processed/* (contracts/data-format.md)."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[float, Field(ge=0, le=1)]


class Record(BaseModel):
    # `_sample` is allowed so contracts/fixtures/processed validates too.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    sample: bool = Field(default=False, alias="_sample")


class ArticleRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    article_id: str
    number: str
    parent_number: str | None
    title: str | None
    text: str


class LawRec(Record):
    law_id: str
    name: str
    former_names: list[str]
    short_names: list[str]
    adopted_date: str | None
    source_url: str
    articles: list[ArticleRec]
    # False = known only by name (cited, text not loaded): target_missing cannot be decided
    text_available: bool = True


class RefRec(Record):
    from_article_id: str
    to_law_id: str
    to_number: str | None
    to_article_id: str | None
    raw_text: str
    matched_name: str
    uses_old_name: bool
    target_missing: bool
    method: Literal["regex", "llm"]
    confidence: Confidence
    # new number from a renumbering table when target_missing, else null
    current_number: str | None = None


class SimilarRec(Record):
    a_article_id: str
    b_article_id: str
    score: Confidence
    model: str


class RelationRec(Record):
    a_article_id: str
    b_article_id: str
    kind: Literal["conflict", "overlap", "consistent"]
    confidence: Confidence
    explanation: str
    model: str


class DraftOpRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["replace", "insert", "delete", "repeal", "add", "rename"]
    law_id: str
    number: str | None
    article_id: str | None
    old_text: str | None
    new_text: str | None
    raw_text: str
    uses_old_name: bool
    target_missing: bool


class DraftRec(Record):
    draft_id: str
    lawforum_id: str
    title: str
    target_law_id: str
    new_name: str | None
    amended_article_ids: list[str]
    cosubmitted_law_ids: list[str]
    source_url: str
    operations: list[DraftOpRec] = []
    cosubmitted_titles: list[str] = []


class IntlSourceRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    kind: Literal["foreign_law", "treaty"]
    country_or_org: str
    title: str
    url: str
    summary: str
    provision: str | None = None


class IntlLinkRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    article_id: str
    source_id: str
    relevance: Confidence
    explanation: str
    model: str | None = None


class InternationalFile(Record):
    sources: list[IntlSourceRec]
    links: list[IntlLinkRec]


class AmendmentRec(Record):
    article_id: str
    reason: str
    suggested_text: str
    based_on_source_ids: list[str]
    model: str
    confidence: Confidence | None = None


JSONL = {
    "laws.jsonl": LawRec,
    "refs.jsonl": RefRec,
    "similar.jsonl": SimilarRec,
    "relations.jsonl": RelationRec,
    "amendments.jsonl": AmendmentRec,
}

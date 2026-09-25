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


class DraftRec(Record):
    draft_id: str
    lawforum_id: str
    title: str
    target_law_id: str
    new_name: str | None
    amended_article_ids: list[str]
    cosubmitted_law_ids: list[str]
    source_url: str


class IntlSourceRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    kind: Literal["foreign_law", "treaty"]
    country_or_org: str
    title: str
    url: str
    summary: str


class IntlLinkRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    article_id: str
    source_id: str
    relevance: Confidence
    explanation: str


class InternationalFile(Record):
    sources: list[IntlSourceRec]
    links: list[IntlLinkRec]


class AmendmentRec(Record):
    article_id: str
    reason: str
    suggested_text: str
    based_on_source_ids: list[str]
    model: str


JSONL = {
    "laws.jsonl": LawRec,
    "refs.jsonl": RefRec,
    "similar.jsonl": SimilarRec,
    "relations.jsonl": RelationRec,
    "amendments.jsonl": AmendmentRec,
}

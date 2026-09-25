"""Fixture registry: fixture file name -> response type (contracts/api.md)."""
import json
from functools import cache

from pydantic import TypeAdapter

from . import config
from .schemas import (Amendment, Article, ArticleConnections, Connections, Draft, DraftDetail, DraftGap, Health,
                      ImpactRequest, ImpactResponse, International, LawDetail, LawSummary, RelationDetail,
                      SearchResponse, ArticleImpactRequest)

RESPONSE_TYPES = {
    "health": Health,
    "laws_list": list[LawSummary],
    "law_detail": LawDetail,
    "law_articles": list[Article],
    "law_connections": Connections,
    "article_connections": ArticleConnections,
    "article_impact": ImpactResponse,
    "impact": ImpactResponse,
    "drafts_list": list[Draft],
    "draft_detail": DraftDetail,
    "draft_gap": DraftGap,
    "article_international": International,
    "article_amendment": Amendment,
    "relation_detail": RelationDetail,
    "search": SearchResponse,
}

REQUEST_BODY_TYPES = {
    "impact": ImpactRequest,
    "article_impact": ArticleImpactRequest,
}


@cache
def load(name: str) -> dict:
    """Full fixture document: {_sample, endpoint, request, response}."""
    with open(config.FIXTURES_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def response(name: str):
    """Fixture response, validated against its contract type."""
    return TypeAdapter(RESPONSE_TYPES[name]).validate_python(load(name)["response"])

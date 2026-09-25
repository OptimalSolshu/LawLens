"""Fixture registry: fixture file name -> response type (contracts/api.md)."""
import json
from functools import cache

from pydantic import TypeAdapter

from . import config
from .models import (
    Amendment,
    ArticleConnections,
    Connections,
    Draft,
    DraftGap,
    ImpactRequest,
    ImpactResponse,
    International,
    LawDetail,
    LawSummary,
)

RESPONSE_TYPES = {
    "laws_list": list[LawSummary],
    "law_detail": LawDetail,
    "law_connections": Connections,
    "article_connections": ArticleConnections,
    "impact": ImpactResponse,
    "drafts_list": list[Draft],
    "draft_gap": DraftGap,
    "article_international": International,
    "article_amendment": Amendment,
}

REQUEST_BODY_TYPES = {
    "impact": ImpactRequest,
}


@cache
def load(name: str) -> dict:
    """Full fixture document: {_sample, endpoint, request, response}."""
    with open(config.FIXTURES_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def response(name: str):
    """Fixture response, validated against its contract type."""
    return TypeAdapter(RESPONSE_TYPES[name]).validate_python(load(name)["response"])

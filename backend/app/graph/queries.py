"""Graph queries behind each endpoint (MOCK=0). Each returns the model named
in contracts/api.md; until implemented they raise NotImplementedError -> 501.
"""
from ..models import (
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


def list_laws(q: str) -> list[LawSummary]:
    raise NotImplementedError("list_laws")


def get_law(law_id: str) -> LawDetail:
    raise NotImplementedError("get_law")


def law_connections(law_id: str) -> Connections:
    raise NotImplementedError("law_connections")


def article_connections(article_id: str) -> ArticleConnections:
    raise NotImplementedError("article_connections")


def impact(req: ImpactRequest) -> ImpactResponse:
    raise NotImplementedError("impact")


def list_drafts() -> list[Draft]:
    raise NotImplementedError("list_drafts")


def draft_gap(draft_id: str) -> DraftGap:
    raise NotImplementedError("draft_gap")


def international(article_id: str) -> International:
    raise NotImplementedError("international")


def amendment(article_id: str) -> Amendment:
    raise NotImplementedError("amendment")

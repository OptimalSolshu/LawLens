from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_store
from ..schemas import (Amendment, ArticleConnections, ArticleImpactRequest, ImpactResponse, International,
                       RelationDetail)
from ..services import impact_service, international_service, law_service
from .params import ArticleId

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("/{article_id}", response_model=ArticleConnections)
def article(article_id: ArticleId, store=Depends(get_store)):
    return law_service.article_connections(store, article_id)


@router.get("/{article_id}/connections", response_model=ArticleConnections)
def article_connections(article_id: ArticleId, store=Depends(get_store)):
    return law_service.article_connections(store, article_id)


@router.get("/{article_id}/impact", response_model=ImpactResponse)
def article_impact(article_id: ArticleId, depth: Annotated[int, Query(ge=1, le=3)] = 2, store=Depends(get_store)):
    return impact_service.for_article(store, article_id, depth=depth)


@router.post("/{article_id}/impact", response_model=ImpactResponse)
def article_impact_change(article_id: ArticleId, body: ArticleImpactRequest, store=Depends(get_store)):
    return impact_service.for_article(store, article_id, new_text=body.new_text, new_name=body.new_name,
                                      new_number=body.new_number, depth=body.depth)


@router.get("/{article_id}/international", response_model=International)
def article_international(article_id: ArticleId, store=Depends(get_store)):
    return international_service.international(store, article_id)


@router.get("/{article_id}/amendment", response_model=Amendment)
def article_amendment(article_id: ArticleId, store=Depends(get_store)):
    return international_service.amendment(store, article_id)


@router.get("/{article_id}/relations/{other_id}", response_model=RelationDetail)
def relation(article_id: ArticleId, other_id: ArticleId, store=Depends(get_store)):
    return international_service.relation_detail(store, article_id, other_id)

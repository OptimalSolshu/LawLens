from fastapi import APIRouter, Depends

from ..deps import get_store
from ..schemas import Article, Connections, LawDetail, LawSummary
from ..services import law_service
from .params import LawId, SearchQ

router = APIRouter(prefix="/api/laws", tags=["laws"])


@router.get("", response_model=list[LawSummary])
def list_laws(q: SearchQ = "", store=Depends(get_store)):
    return law_service.list_laws(store, q)


@router.get("/{law_id}", response_model=LawDetail)
def get_law(law_id: LawId, store=Depends(get_store)):
    return law_service.get_law(store, law_id)


@router.get("/{law_id}/articles", response_model=list[Article])
def law_articles(law_id: LawId, store=Depends(get_store)):
    return law_service.list_articles(store, law_id)


@router.get("/{law_id}/connections", response_model=Connections)
def law_connections(law_id: LawId, store=Depends(get_store)):
    return law_service.law_connections(store, law_id)

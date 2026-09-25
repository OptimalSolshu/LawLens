from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from .. import config
from ..deps import get_store
from ..schemas import Draft, DraftDetail, DraftGap, Health, ImpactRequest, ImpactResponse, SearchResponse
from ..services import draft_service, export_service, impact_service, search_service
from .params import DraftId, OptArticleId, OptDraftId, OptLawId, SearchQ

router = APIRouter(prefix="/api")


@router.get("/health", response_model=Health, tags=["meta"])
def health(store=Depends(get_store)):
    return Health(status="ok", mock=config.MOCK, dataset=store.dataset, graph=store.backend)


@router.post("/impact", response_model=ImpactResponse, tags=["impact"])
def impact(req: ImpactRequest, store=Depends(get_store)):
    return impact_service.compute(store, req)


@router.get("/drafts", response_model=list[Draft], tags=["drafts"])
def list_drafts(store=Depends(get_store)):
    return draft_service.list_drafts(store)


@router.get("/drafts/{draft_id}", response_model=DraftDetail, tags=["drafts"])
def draft(draft_id: DraftId, store=Depends(get_store)):
    return draft_service.detail(store, draft_id)


@router.get("/drafts/{draft_id}/gap", response_model=DraftGap, tags=["drafts"])
def draft_gap(draft_id: DraftId, store=Depends(get_store)):
    return draft_service.gap(store, draft_id)


@router.get("/drafts/{draft_id}/gaps", response_model=DraftGap, tags=["drafts"])
def draft_gaps(draft_id: DraftId, store=Depends(get_store)):
    return draft_service.gap(store, draft_id)


@router.get("/search", response_model=SearchResponse, tags=["search"])
def search(q: SearchQ = "", store=Depends(get_store)):
    return search_service.search(store, q)


@router.get("/export", tags=["export"], response_class=Response,
            responses={200: {"content": {"text/csv": {}}, "description": "UTF-8 CSV"}})
def export(
    kind: Annotated[str, Query(max_length=40)],
    article_id: OptArticleId = None,
    law_id: OptLawId = None,
    draft_id: OptDraftId = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    list: Annotated[str | None, Query(max_length=40)] = None,  # noqa: A002 - public query name
    new_text: Annotated[str | None, Query(max_length=4000)] = None,
    new_name: Annotated[str | None, Query(max_length=300)] = None,
    new_number: Annotated[str | None, Query(pattern=r"^\d+(\.\d+)*$")] = None,
    depth: Annotated[int, Query(ge=1, le=3)] = 2,
    store=Depends(get_store),
):
    data = export_service.rows(store, kind, article_id=article_id, law_id=law_id, draft_id=draft_id, q=q,
                               list_name=list, new_text=new_text, new_name=new_name, new_number=new_number,
                               depth=depth)
    name = f"lawlens-{kind}{'-' + list if list else ''}.csv"
    return Response(export_service.to_csv(data), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})

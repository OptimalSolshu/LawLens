"""LawLens API. MOCK=1 serves contracts/fixtures; MOCK=0 queries Neo4j (app/graph)."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, fixtures
from .graph import queries
from .models import (
    Amendment,
    ArticleConnections,
    Connections,
    Draft,
    DraftGap,
    Health,
    ImpactRequest,
    ImpactResponse,
    International,
    LawDetail,
    LawSummary,
)

app = FastAPI(title="LawLens API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def mark_sample(request: Request, call_next):
    response = await call_next(request)
    if config.MOCK:
        response.headers["X-LawLens-Sample"] = "true"
    return response


@app.exception_handler(NotImplementedError)
async def not_implemented(_: Request, exc: NotImplementedError):
    return JSONResponse(status_code=501, content={"detail": f"not implemented: {exc}"})


@app.get("/api/health", response_model=Health)
def health():
    return Health(status="ok", mock=config.MOCK)


@app.get("/api/laws", response_model=list[LawSummary])
def list_laws(q: str = ""):
    if not config.MOCK:
        return queries.list_laws(q)
    laws = fixtures.response("laws_list")
    needle = q.strip().casefold()
    if not needle:
        return laws
    return [l for l in laws if any(needle in n.casefold() for n in [l.name, *l.former_names])]


@app.get("/api/laws/{law_id}", response_model=LawDetail)
def get_law(law_id: str):
    return fixtures.response("law_detail") if config.MOCK else queries.get_law(law_id)


@app.get("/api/laws/{law_id}/connections", response_model=Connections)
def law_connections(law_id: str):
    return fixtures.response("law_connections") if config.MOCK else queries.law_connections(law_id)


@app.get("/api/articles/{article_id}", response_model=ArticleConnections)
def article_connections(article_id: str):
    return fixtures.response("article_connections") if config.MOCK else queries.article_connections(article_id)


@app.post("/api/impact", response_model=ImpactResponse)
def impact(req: ImpactRequest):
    return fixtures.response("impact") if config.MOCK else queries.impact(req)


@app.get("/api/drafts", response_model=list[Draft])
def list_drafts():
    return fixtures.response("drafts_list") if config.MOCK else queries.list_drafts()


@app.get("/api/drafts/{draft_id}/gap", response_model=DraftGap)
def draft_gap(draft_id: str):
    return fixtures.response("draft_gap") if config.MOCK else queries.draft_gap(draft_id)


@app.get("/api/articles/{article_id}/international", response_model=International)
def article_international(article_id: str):
    return fixtures.response("article_international") if config.MOCK else queries.international(article_id)


@app.get("/api/articles/{article_id}/amendment", response_model=Amendment)
def article_amendment(article_id: str):
    return fixtures.response("article_amendment") if config.MOCK else queries.amendment(article_id)

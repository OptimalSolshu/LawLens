"""LawLens API.

MOCK=1  -> [ЖИШЭЭ] sample dataset (contracts/fixtures/processed), in-memory graph, no Neo4j / LLM / network.
MOCK=0  -> real data/processed via Neo4j (GRAPH_BACKEND=neo4j) or in memory (GRAPH_BACKEND=memory).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .deps import get_store
from .routers import articles, laws, misc

log = logging.getLogger("lawlens")



@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_graph()
    yield


def seed_graph() -> None:
    """docker compose (MOCK=0, SEED_ON_START=1): load data/processed into an empty Neo4j."""
    if config.MOCK or config.GRAPH_BACKEND != "neo4j" or not config.SEED_ON_START:
        return
    from .graph.loader import is_empty, load

    if is_empty():
        log.info("empty graph: loading %s", config.PROCESSED_DIR)
        load(config.PROCESSED_DIR, reset=False)


app = FastAPI(title="LawLens API", version="0.2.0", lifespan=lifespan,
              description="Хуулийн уялдааны шинжилгээ. Facts and suggestions are separate; nothing here is a legal verdict.")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["*"], expose_headers=["Content-Disposition", "X-LawLens-Sample"])


@app.middleware("http")
async def mark_sample(request: Request, call_next):
    response = await call_next(request)
    if config.MOCK:
        response.headers["X-LawLens-Sample"] = "true"
    return response


app.include_router(misc.router)
app.include_router(laws.router)
app.include_router(articles.router)

__all__ = ["app", "get_store"]

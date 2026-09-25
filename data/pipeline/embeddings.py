"""Embeddings for similar.jsonl (backend/app/ai/embeddings.py).

BAAI/bge-m3 by default (EMBED_MODEL; needs requirements-ml.txt), deterministic
offline fallback "demo-ngram-v1" otherwise. Pairs are computed in pipeline.build.
"""
from . import _backend  # noqa: F401
from app.ai.embeddings import (DemoEmbedder, SentenceTransformerEmbedder, cosine, get_embedder,  # noqa: E402
                               min_score)

__all__ = ["DemoEmbedder", "SentenceTransformerEmbedder", "cosine", "get_embedder", "min_score"]

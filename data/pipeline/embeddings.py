"""bge-m3 article embeddings + similar pairs -> processed/similar.jsonl.

Needs requirements-ml.txt (sentence-transformers).
"""
MODEL = "BAAI/bge-m3"  # 1024-dim, matches the Neo4j vector index in backend/app/graph/schema.cypher
MIN_SCORE = 0.75


def embed(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL)
    return model.encode(texts, normalize_embeddings=True).tolist()


def similar_pairs() -> None:
    raise NotImplementedError("TODO(member 3): cross-law pairs with score >= MIN_SCORE")

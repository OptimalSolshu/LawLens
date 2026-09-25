"""Embedding abstraction for "provisions regulating the same matter" (suggestions).

- SentenceTransformerEmbedder: BAAI/bge-m3 by default (EMBED_MODEL), 1024-dim,
  same dimension as the Neo4j vector index. Needs sentence-transformers and a
  downloaded model; never used in MOCK mode.
- DemoEmbedder: deterministic, offline, dependency-free hashed bag of word
  stems + character trigrams, also 1024-dim. Its model name
  "demo-ngram-v1" is stored on every result so the UI can say "Демо similarity".

Scores from different models are not comparable, so each model has its own
threshold (MIN_SCORE).
"""
import hashlib
import math
import os
import re
from typing import Protocol

from ..parser.normalize import stem, tokens

DIM = 1024
DEMO_MODEL = "demo-ngram-v1"
DEFAULT_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
MIN_SCORE = {"BAAI/bge-m3": 0.75, "intfloat/multilingual-e5-large": 0.80, DEMO_MODEL: 0.60}

# Legal boilerplate that says nothing about the regulated matter.
_STOP = {
    "хуул", "хууль", "тухай", "заасан", "заасны", "заас", "энэ", "дагуу", "байна", "бол", "нь", "болон",
    "хэсэг", "хэсг", "зүйл", "зүйлийн", "дах", "дэх", "эсх", "эсхүл", "бөгөөд", "тохиолдолд", "жишээ",
}
_SAMPLE_TAG = re.compile(r"\[ЖИШЭЭ\]\s*")


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _bucket(feature: str) -> int:
    return int.from_bytes(hashlib.md5(feature.encode()).digest()[:4], "little") % DIM


def clean_text(text: str) -> str:
    return _SAMPLE_TAG.sub("", text or "")


class DemoEmbedder:
    model = DEMO_MODEL

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        words = [stem(t) for t in tokens(clean_text(text)) if not t[:1].isdigit()]
        words = [w for w in words if w not in _STOP and len(w) > 2]
        for w in words:
            vec[_bucket("w:" + w)] += 1.0
            padded = f"#{w}#"
            for i in range(len(padded) - 2):
                vec[_bucket("c:" + padded[i:i + 3])] += 0.3
        vec = [math.sqrt(v) for v in vec]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedder:
    def __init__(self, model: str = DEFAULT_MODEL):
        from sentence_transformers import SentenceTransformer  # optional heavy dependency

        self.model = model
        self._st = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        prefix = "passage: " if "e5" in self.model else ""
        return self._st.encode([prefix + clean_text(t) for t in texts], normalize_embeddings=True).tolist()


def get_embedder(prefer_real: bool = False) -> Embedder:
    """Real model only when asked for and importable; otherwise the demo fallback."""
    if prefer_real:
        try:
            return SentenceTransformerEmbedder()
        except Exception:  # model not installed / not downloaded / offline
            pass
    return DemoEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def min_score(model: str) -> float:
    return MIN_SCORE.get(model, 0.75)


def is_demo(model: str) -> bool:
    return model == DEMO_MODEL

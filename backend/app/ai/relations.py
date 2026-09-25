"""LLMRelationService: conflict / overlap / consistent judgements (suggestions only).

Implementations:
- PrecomputedRelationService: offline. Serves curated, cached judgements
  (data/fixtures/sample/relations.json or an LLM cache file) and falls back to
  a transparent heuristic (model "demo-heuristic") for pairs it has not seen.
- AnthropicRelationService: Claude via the Anthropic SDK with structured
  output, results cached on disk so the UI never waits on an LLM call.

Every result carries confidence, explanation and model, and is shown as
"Санал" — never as a legal conclusion.
"""
import hashlib
import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .embeddings import clean_text

Kind = Literal["conflict", "overlap", "consistent"]


class Provision(BaseModel):
    article_id: str
    law_name: str
    number: str
    text: str


class Judgement(BaseModel):
    kind: Kind
    confidence: float = Field(ge=0, le=1)
    explanation: str
    model: str


class Resolution(BaseModel):
    article_id: str | None = None  # the provision the suggested wording is for
    suggested_text: str
    reason: str
    based_on_source_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    model: str


class LLMRelationService(ABC):
    @abstractmethod
    def classify_relation(self, a: Provision, b: Provision) -> tuple[Kind, float, str]:
        """(kind, confidence, model)"""

    @abstractmethod
    def explain_relation(self, a: Provision, b: Provision, kind: Kind) -> str: ...

    @abstractmethod
    def suggest_resolution(self, a: Provision, b: Provision, judgement: Judgement,
                           sources: list[dict]) -> Resolution | None: ...

    def judge(self, a: Provision, b: Provision) -> Judgement:
        kind, conf, model = self.classify_relation(a, b)
        return Judgement(kind=kind, confidence=conf, explanation=self.explain_relation(a, b, kind), model=model)


# ---- offline -----------------------------------------------------------------

_QTY = re.compile(r"(\d+)\s*(цаг|хоног|хувь|сар|жил|нэгж)")
_WORD_QTY = {"жил бүр": ("1", "жил"), "хоёр жил": ("2", "жил"), "гурван жил": ("3", "жил")}


def _quantities(text: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for n, unit in _QTY.findall(text):
        out.setdefault(unit, set()).add(n)
    for phrase, (n, unit) in _WORD_QTY.items():
        if phrase in text.lower():
            out.setdefault(unit, set()).add(n)
    return out


class PrecomputedRelationService(LLMRelationService):
    HEURISTIC = "demo-heuristic"

    def __init__(self, curated_file: Path | None = None):
        self._curated: dict[frozenset, dict] = {}
        if curated_file and curated_file.exists():
            for rec in json.loads(curated_file.read_text(encoding="utf-8"))["pairs"]:
                self._curated[frozenset((rec["a"], rec["b"]))] = rec

    def curated(self, a: Provision, b: Provision) -> dict | None:
        return self._curated.get(frozenset((a.article_id, b.article_id)))

    def classify_relation(self, a, b):
        if rec := self.curated(a, b):
            return rec["kind"], rec["confidence"], rec["model"]
        qa, qb = _quantities(clean_text(a.text)), _quantities(clean_text(b.text))
        clash = [u for u in qa.keys() & qb.keys() if qa[u] != qb[u]]
        if clash:
            return "conflict", 0.55, self.HEURISTIC
        return "overlap", 0.5, self.HEURISTIC

    def explain_relation(self, a, b, kind):
        if rec := self.curated(a, b):
            return rec["explanation"]
        if kind == "conflict":
            return (f"{a.law_name}-ийн {a.number} болон {b.law_name}-ийн {b.number}-д ижил төрлийн хэмжээг "
                    f"өөр өөрөөр заасан байж болзошгүй. Автомат дүрмийн санал; шалгах шаардлагатай.")
        return (f"{a.law_name}-ийн {a.number} болон {b.law_name}-ийн {b.number} ижил асуудлыг зохицуулж "
                f"байж болзошгүй. Автомат дүрмийн санал; шалгах шаардлагатай.")

    def suggest_resolution(self, a, b, judgement, sources):
        rec = self.curated(a, b)
        if not rec or not rec.get("resolution"):
            return None
        r = rec["resolution"]
        return Resolution(article_id=r.get("article_id"), suggested_text=r["suggested_text"], reason=r["reason"],
                          based_on_source_ids=r["based_on_source_ids"], confidence=r["confidence"],
                          model=rec["model"])


# ---- Claude ------------------------------------------------------------------

SYSTEM = """Та Монгол Улсын Их Хурлын Тамгын газрын хууль зүйн шинжээчид туслах хэрэгсэл.
Хоёр хуулийн заалтыг харьцуулж, харилцааг нэг ангиллаар тодорхойлно:
- conflict: нэг харилцааг хоорондоо нийцэхгүй байдлаар зохицуулсан байж болзошгүй;
- overlap: ижил харилцааг давхардуулан зохицуулсан байж болзошгүй;
- consistent: хоорондоо нийцэж байна.
Та эцсийн дүгнэлт гаргахгүй. Тайлбарыг албан ёсны монгол хэлээр, хоёр заалтын хууль, дугаарыг
нэрлэж 2-3 өгүүлбэрээр бичнэ. "зөрчилтэй" гэж эцсийн дүгнэлт хэлбэрээр бүү бич;
"байж болзошгүй", "шалгах шаардлагатай" гэсэн үг хэллэг хэрэглэнэ. Зөвхөн өгөгдсөн бичвэрт тулгуурла."""

RESOLUTION_SYSTEM = SYSTEM + """
Шийдлийн санал гаргахдаа зөвхөн өгөгдсөн эх сурвалжид (олон улсын болон гадаад орны жишээ) тулгуурлаж,
ашигласан эх сурвалжийн source_id-г based_on_source_ids-д заавал бичнэ."""


class _Out(BaseModel):
    kind: Kind
    confidence: float = Field(ge=0, le=1)
    explanation: str


class _ResOut(BaseModel):
    suggested_text: str
    reason: str
    based_on_source_ids: list[str]
    confidence: float = Field(ge=0, le=1)


class AnthropicRelationService(LLMRelationService):
    def __init__(self, model: str | None = None, cache_dir: Path | None = None):
        import anthropic

        self.model = model or os.getenv("LLM_MODEL", "claude-opus-5")
        self.client = anthropic.Anthropic()  # credentials from env / `ant auth login`, never hard-coded
        self.cache_dir = cache_dir
        self._last: dict[frozenset, _Out] = {}

    def _cached(self, key: str, fn):
        path = self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json" if self.cache_dir else None
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        out = fn()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return out

    def _parse(self, system: str, user: str, schema):
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=4096,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model declined the request")
        return response.parsed_output.model_dump()

    @staticmethod
    def _pair_prompt(a: Provision, b: Provision) -> str:
        return (f"Заалт A: {a.law_name}, {a.number}\n{clean_text(a.text)}\n\n"
                f"Заалт B: {b.law_name}, {b.number}\n{clean_text(b.text)}")

    def _judge_raw(self, a, b) -> _Out:
        key = frozenset((a.article_id, b.article_id))
        if key not in self._last:
            prompt = self._pair_prompt(a, b)
            data = self._cached(self.model + "|rel|" + prompt, lambda: self._parse(SYSTEM, prompt, _Out))
            self._last[key] = _Out(**data)
        return self._last[key]

    def classify_relation(self, a, b):
        out = self._judge_raw(a, b)
        return out.kind, out.confidence, self.model

    def explain_relation(self, a, b, kind):
        return self._judge_raw(a, b).explanation

    def suggest_resolution(self, a, b, judgement, sources):
        if judgement.kind == "consistent" or not sources:
            return None
        src = "\n".join(f"- {s['source_id']}: {s['title']} ({s.get('provision') or ''}) {s['summary']}" for s in sources)
        prompt = f"{self._pair_prompt(a, b)}\n\nДүгнэлт: {judgement.kind}\n{judgement.explanation}\n\nЭх сурвалж:\n{src}"
        data = self._cached(self.model + "|res|" + prompt, lambda: self._parse(RESOLUTION_SYSTEM, prompt, _ResOut))
        allowed = {s["source_id"] for s in sources}
        data["based_on_source_ids"] = [i for i in data["based_on_source_ids"] if i in allowed]
        return Resolution(model=self.model, article_id=a.article_id, **data)


def get_relation_service(curated_file: Path | None = None, cache_dir: Path | None = None,
                         use_llm: bool = False) -> LLMRelationService:
    if use_llm and os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicRelationService(cache_dir=cache_dir)
    return PrecomputedRelationService(curated_file)

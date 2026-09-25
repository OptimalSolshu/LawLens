"""Claude-backed suggestions (relations.jsonl, amendments.jsonl): backend/app/ai/relations.py.

AnthropicRelationService uses the Anthropic SDK with structured output and a
disk cache (data/cache/llm) so the API never calls an LLM per request.
PrecomputedRelationService serves curated/cached judgements offline.
"""
from . import _backend  # noqa: F401
from app.ai.relations import (AnthropicRelationService, LLMRelationService,  # noqa: E402
                              PrecomputedRelationService, get_relation_service)

__all__ = ["AnthropicRelationService", "LLMRelationService", "PrecomputedRelationService", "get_relation_service"]

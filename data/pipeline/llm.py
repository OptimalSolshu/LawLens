"""Claude calls: conflict/overlap judgement (relations.jsonl), international
links, amendment suggestions (amendments.jsonl). Every output records `model`
and a confidence, and is shown to users as a *suggestion*, never as fact.
"""
import os

import anthropic

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5")


def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def ask(prompt: str, max_tokens: int = 1024) -> str:
    msg = client().messages.create(model=MODEL, max_tokens=max_tokens,
                                   messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if b.type == "text")


def judge_relation(a_text: str, b_text: str) -> dict:
    raise NotImplementedError("TODO(member 3): return {kind, confidence, explanation}")


def suggest_amendment(article_text: str, context: list[str]) -> dict:
    raise NotImplementedError("TODO(member 3): return {reason, suggested_text, based_on_source_ids}")

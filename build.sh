#!/usr/bin/env bash
# PDF → JSON → Neo4j → утгын холбоос бүтэн дамжуулга
set -euo pipefail
cd "$(dirname "$0")"
PDF="${1:-data/labor_law_2021.pdf}"
ID="${2:-labor-2021}"
OUT="data/${ID}.json"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
docker compose up -d
until curl -s -o /dev/null http://localhost:7474; do sleep 2; done
.venv/bin/python parse_law.py "$PDF" --id "$ID" -o "$OUT"
.venv/bin/python load_neo4j.py "$OUT" --reset
# Embedding: SIMILAR_TO, RELATED_TO, Topic (локал, үнэгүй)
.venv/bin/python semantic_links.py --law "$ID"
# LLM хэм хэмжээ: Norm, ишлэлийн үүрэг (Claude API түлхүүр эсвэл кэш байвал)
if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -f "data/${ID}.norms.json" ]; then
  .venv/bin/python extract_norms.py --law "$ID"
else
  echo "  ANTHROPIC_API_KEY байхгүй тул extract_norms.py алгаслаа"
fi

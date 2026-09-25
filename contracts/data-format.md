# Data format contract

Files produced by **data/** (member 3) in `data/processed/` and consumed by
**backend/app/graph/loader.py** (member 1). Changes to this file only via PR
reviewed by all three members.

Machine-checkable version: `data/pipeline/schemas.py`. Run `make validate-data`
before pushing processed files. Small SAMPLE copies of every file live in
`contracts/fixtures/processed/` so the loader can be built before real data
exists. Their records carry `"_sample": true`. Real output must not.

## Conventions

- Encoding UTF-8, `.jsonl` = one JSON object per line.
- **law_id**: ASCII slug of the law's *current* name, Mongolian Cyrillic
  transliterated with `pipeline.ids.law_id()`. Example:
  `Зөвшөөрлийн тухай хууль` → `zovshoorliin-tukhai-khuuli`.
- **article_id**: `"{law_id}:{number}"`, e.g. `zovshoorliin-tukhai-khuuli:15.1`.
  `number` is the provision number as printed (`15`, `15.1`, `15.1.3`).
- `confidence` and `score` are floats in `[0, 1]`.
- `model` is the model identifier that produced a record (`"regex"` is not a
  model; regex records use `method` instead).
- Dates are ISO `YYYY-MM-DD`; unknown = `null`.

## laws.jsonl

One line per law (current and repealed laws that are still referenced).

```json
{"law_id": "zovshoorliin-tukhai-khuuli",
 "name": "Зөвшөөрлийн тухай хууль",
 "former_names": ["Тусгай зөвшөөрлийн тухай хууль"],
 "short_names": [],
 "adopted_date": "2000-01-01",
 "source_url": "https://legalinfo.mn/...",
 "articles": [
   {"article_id": "zovshoorliin-tukhai-khuuli:15", "number": "15",
    "parent_number": null, "title": "...", "text": "..."},
   {"article_id": "zovshoorliin-tukhai-khuuli:15.1", "number": "15.1",
    "parent_number": "15", "title": null, "text": "..."}
 ]}
```

`former_names` come from `data/law_names.json` (`{"current name": ["former name", ...]}`).

## refs.jsonl

One line per detected citation.

| field | type | notes |
|---|---|---|
| from_article_id | str | the citing provision |
| to_law_id | str | resolved via current OR former name |
| to_number | str \| null | cited provision number; null = whole law cited |
| to_article_id | str \| null | null when the target does not exist |
| raw_text | str | exact citation text as it appears in the source |
| matched_name | str | the law name string that matched |
| uses_old_name | bool | `matched_name` is one of the target law's `former_names` |
| target_missing | bool | `to_number` given but no such article (repealed/renumbered) |
| method | `"regex"` \| `"llm"` | |
| confidence | float | regex ≈ 0.95+, llm as reported |

## similar.jsonl

`{a_article_id, b_article_id, score, model}`. Unordered pair, stored once with
`a_article_id < b_article_id`. Only pairs from **different** laws, score ≥ 0.75.

## relations.jsonl

`{a_article_id, b_article_id, kind: "conflict"|"overlap"|"consistent",
confidence, explanation, model}`. LLM judgement on a similar pair. The
`explanation` is written in Mongolian and names both provisions.

## drafts.json

JSON array:
`[{draft_id, lawforum_id, title, target_law_id, new_name|null,
amended_article_ids[], cosubmitted_law_ids[], source_url}]`

`draft_id` = `"draft-{lawforum_id}"`. `new_name` is set when the bill renames
the law.

## international.json

```json
{"sources": [{"source_id": "...", "kind": "foreign_law"|"treaty",
              "country_or_org": "...", "title": "...", "url": "...",
              "summary": "..."}],
 "links":   [{"article_id": "...", "source_id": "...",
              "relevance": 0.0, "explanation": "..."}]}
```

Sources are curated by hand in `data/international/`. Links may be produced by
the LLM.

## amendments.jsonl

`{article_id, reason, suggested_text, based_on_source_ids[], model}`, an
AI suggestion. `based_on_source_ids` may contain international `source_id`s
and `article_id`s.

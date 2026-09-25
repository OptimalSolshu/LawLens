# Data format contract

Files produced by **data/** (member 3) in `data/processed/` and consumed by
**backend/app/graph/loader.py** (member 1). Changes to this file only via PR
reviewed by all three members.

Machine-checkable version: `data/pipeline/schemas.py` (schema) and
`data/pipeline/validate.py` (referential integrity). Run `make validate-data`
(`python scripts/validate_data.py`, non-zero exit on any problem) before pushing
processed files.

Two datasets use this format:

| directory | content | produced by |
|---|---|---|
| `data/processed/` | REAL data (Labor Law text from legalinfo.mn, parsed) | `scripts/build_processed_data.py` |
| `contracts/fixtures/processed/` | invented **[ЖИШЭЭ]** sample dataset for the offline demo (`MOCK=1`) | `scripts/seed_demo.py` from `data/fixtures/sample/` |

Sample records carry `"_sample": true` and every sample provision text starts with
`[ЖИШЭЭ]`; real output must not carry `_sample`. Replacing the sample with real
data changes no API shape: point `PROCESSED_DIR` at a directory in this format.

Fields marked *(v0.2)* are additive and optional (defaults shown); older files stay valid.

## Conventions

- Encoding UTF-8, `.jsonl` = one JSON object per line.
- **law_id**: stable ASCII slug (`[a-z0-9-]+`). A parsed law keeps the id it
  was given with `parse_law.py --id` (e.g. `labor-2021`), so it survives a
  rename. A law known only by name (cited, not parsed) gets
  `pipeline.ids.law_id(name)`, e.g.
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

`former_names` / `short_names` come from `data/law_names.json` (below).
*(v0.2)* `text_available: bool = true` — `false` for a law that is only cited by
name (no text loaded; `articles: []`). For such laws `target_missing` cannot be
decided and stays `false`; `source_url` is its legalinfo.mn entry if known.

Validation: unique `law_id` and `article_id`; `article_id` starts with its
`law_id`; `parent_number` exists; `source_url` is https.

Produced from `parse_law.py` output by `python -m pipeline.from_lawgraph`
(run from `data/`). Repealed provisions are not listed, so a reference to one
has `target_missing: true`.

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
| method | `"regex"` \| `"llm"` | regex = fact, llm = suggestion |
| confidence | float | regex = 1.0 (fact), llm as reported |
| current_number | str \| null | *(v0.2)* new number from a renumbering table when `target_missing`, else null |

Validation: `from_article_id` exists; `to_law_id` is in laws.jsonl; `to_article_id`
exists when set; for laws with text, `target_missing` is true exactly when
`to_number` is not one of the law's provision numbers; regex refs have confidence 1.0.

## similar.jsonl

`{a_article_id, b_article_id, score, model}`. Unordered pair, stored once with
`a_article_id < b_article_id`. Only pairs from **different** laws with **no direct
citation** between them, score ≥ the model's threshold (`app/ai/embeddings.py`
`MIN_SCORE`: BAAI/bge-m3 0.75, intfloat/multilingual-e5-large 0.80, offline
`demo-ngram-v1` 0.60 — scores of different models are not comparable).

## relations.jsonl

`{a_article_id, b_article_id, kind: "conflict"|"overlap"|"consistent",
confidence, explanation, model}`. LLM judgement on a similar pair. The
`explanation` is written in Mongolian and names both provisions.

## drafts.json

JSON array:
`[{draft_id, lawforum_id, title, target_law_id, new_name|null,
amended_article_ids[], cosubmitted_law_ids[], source_url}]`

`draft_id` = `"draft-{lawforum_id}"`. `new_name` is set when the bill renames
the law. *(v0.2)* `operations: DraftOp[] = []` — amendment operations parsed from
the bill text (`{op: replace|insert|delete|repeal|add|rename, law_id, number,
article_id, old_text, new_text, raw_text, uses_old_name, target_missing}`);
`cosubmitted_titles: str[] = []` — titles of the co-submitted bills;
`cosubmitted_law_ids` is resolved from those titles. Every law / article id must exist.

## international.json

```json
{"sources": [{"source_id": "...", "kind": "foreign_law"|"treaty",
              "country_or_org": "...", "title": "...", "url": "...",
              "summary": "...", "provision": "Article 2"}],
 "links":   [{"article_id": "...", "source_id": "...",
              "relevance": 0.0, "explanation": "...", "model": "..."}]}
```

Sources are curated by hand in `data/international/sources.json` (only pages a
person has opened); *(v0.2)* `provision` names the article/regulation. Links
(`data/international/links.json` for real data) are suggestions and must name their
`model`. Validation: every link's `article_id` and `source_id` exist; urls are https.

## amendments.jsonl

`{article_id, reason, suggested_text, based_on_source_ids[], model, confidence}`, an
AI suggestion (*(v0.2)* `confidence` optional). `based_on_source_ids` may contain
international `source_id`s and `article_id`s.

## data/law_names.json

Name registry used by the parser: every variant resolves to the canonical law, and
the longest matching name always wins.

```json
{"laws": [{"current_name": "Зөвшөөрлийн тухай хууль",
           "former_names": ["Тусгай зөвшөөрлийн тухай хууль"],
           "short_names": [], "aliases": [],
           "law_id": null, "source_url": null}]}
```

`law_id` defaults to the slug of `current_name` (a parsed law keeps its own id);
`source_url` (optional) is used for name-only laws. The legacy map
`{"current name": ["former", ...]}` is still read. Parsed laws also contribute their
own `name`, `former_names`, `short_names`.

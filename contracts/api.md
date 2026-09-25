# API contract

Served by **backend/** (member 1), consumed by **web/** (member 2). Changes
only via PR reviewed by all three.

- Source of truth in code: `backend/app/models.py` (pydantic) mirrored by
  `web/src/types.ts`. `backend/tests/test_contracts.py` fails if any fixture
  drifts from the models.
- Every endpoint has a fixture in `contracts/fixtures/<name>.json` of the form
  `{"_sample": true, "endpoint": "...", "request": {...}, "response": ...}`.
  With `MOCK=1` the API returns `response` unchanged, ignoring path ids
  (except `GET /api/laws?q=`, which is filtered). Mock responses carry
  the header `X-LawLens-Sample: true`.
- All fixture content is **invented SAMPLE data** (texts are prefixed
  `[ЖИШЭЭ]`, links point to `example.org`). It is not real legal content.
- Base path `/api`. JSON, UTF-8. Errors: FastAPI default `{"detail": ...}`;
  `501` = endpoint not implemented yet in non-mock mode.

## Reliability rules (apply to every result)

1. Every item cites **law + provision + link**: `law_id`, `law_name`,
   `number`, `source_url`.
2. `type: "fact"` = deterministic (parsed text, regex citation, stored name
   history). `type: "suggestion"` = produced by embeddings or an LLM.
   The UI must show them visually separated, and always show `confidence`.
3. Suggestions carry an `explanation`.

## Common types

```ts
RefItem {
  law_id: string, law_name: string,
  article_id: string | null,     // null when the provision does not exist
  number: string | null,         // null when the whole law is meant
  snippet: string,               // citation context / provision excerpt
  source_url: string,
  type: "fact" | "suggestion",
  confidence: number,            // 0..1
  flags: { uses_old_name: boolean, target_missing: boolean },
  anchor_number?: string | null, // provision number on the SELECTED side
  score?: number | null,         // similarity score (similar lists)
  explanation?: string | null
}
LawGroup { law_id: string, law_name: string, count: number, items: RefItem[] }
```

**Item semantics:** a `RefItem` always describes the *other* provision, the
one that is not the selected law/article. `anchor_number` names the provision
on the selected side, so a law-level list can render
`Зөрчлийн тухай хууль 11.4 → 15.1`.

`LawGroup.count == items.length`. Groups are sorted by `count` desc.

## Connection lists

Returned by the law and article connection endpoints:

| key | content |
|---|---|
| incoming | refs from other laws' provisions to the selection, grouped by citing law |
| outgoing | refs from the selection to other provisions, grouped by cited law |
| former_name_refs | subset of incoming ∪ outgoing where `flags.uses_old_name` |
| missing_target_refs | subset of incoming ∪ outgoing where `flags.target_missing` |
| similar | `RefItem[]` (`type:"suggestion"`, `score` set), sorted by score |
| conflicts | `RefItem[]` from relations with `kind:"conflict"` (`type:"suggestion"`) |
| totals | item counts per list: `{incoming, outgoing, former_name_refs, missing_target_refs, similar, conflicts}` |

---

## GET /api/health

`{"status": "ok", "mock": true}`

## GET /api/laws?q=

`q` is optional and matches (case-insensitive substring) current **and**
former names. Fixture: `laws_list.json`.

```json
[{"law_id": "zovshoorliin-tukhai-khuuli", "name": "Зөвшөөрлийн тухай хууль",
  "former_names": ["Тусгай зөвшөөрлийн тухай хууль"], "article_count": 2}]
```

`GET /api/laws?q=Тусгай` returns the law above.

## GET /api/laws/{law_id}

Fixture: `law_detail.json`.

```json
{"law": {"law_id": "...", "name": "...", "former_names": [], "short_names": [],
         "adopted_date": "2020-01-01", "source_url": "..."},
 "articles": [{"article_id": "...:15.1", "number": "15.1",
               "title": "...", "text": "..."}]}
```

## GET /api/laws/{law_id}/connections

Fixture: `law_connections.json`. Shape:
`{incoming, outgoing, former_name_refs, missing_target_refs, similar, conflicts, totals}`
(see *Connection lists*).

## GET /api/articles/{article_id}

Fixture: `article_connections.json`. Same shape as connections plus
`article: {article_id, number, title, text, law_id, law_name, source_url}`.

## POST /api/impact

Fixture: `impact.json`. Request (at least one of `law_id`/`article_id`):

```json
{"article_id": "zovshoorliin-tukhai-khuuli:15.1",
 "new_text": "...", "new_name": null, "depth": 2}
```

`depth` is 1..3 (422 otherwise). Depth 1 = provisions citing the changed
provision/law. Depth *n* = provisions citing depth *n-1*. A provision appears
only at its smallest depth. `new_name` set = rename: every reference to the
law becomes a former-name reference. `new_similar` = provisions similar to
`new_text` (suggestions).

```json
{"depths": [{"depth": 1, "count": 1, "groups": [LawGroup]}],
 "new_similar": [RefItem],
 "totals": {"laws": 2, "articles": 2, "new_similar": 1}}
```

## GET /api/drafts

Fixture: `drafts_list.json`. Array of drafts, same fields as
`drafts.json` in data-format.md.

## GET /api/drafts/{draft_id}/gap

Fixture: `draft_gap.json`. Laws whose provisions cite the amended provisions
(or the renamed law), split into those co-submitted in the bill's package
(`covered`) and those not (`missing`). `found` = number of laws in covered +
missing.

```json
{"draft_id": "...", "found": 2, "covered": [LawGroup], "missing": [LawGroup]}
```

## GET /api/articles/{article_id}/international

Fixture: `article_international.json`.

```json
{"article_id": "...",
 "foreign_laws": [IntlItem], "treaties": [IntlItem]}
IntlItem {source_id, kind: "foreign_law"|"treaty", country_or_org, title, url,
          summary, relevance, explanation, type: "suggestion"}
```

## GET /api/articles/{article_id}/amendment

Fixture: `article_amendment.json`.

```json
{"article_id": "...", "suggested_text": "...", "reason": "...",
 "sources": [{"kind": "law_article"|"foreign_law"|"treaty", "id": "...",
              "title": "...", "url": "..."}],
 "type": "suggestion", "confidence": 0.7, "model": "..."}
```

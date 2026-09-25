# LawLens — Хуулийн уялдааны шинжилгээ

A knowledge graph and impact-analysis tool centred on the Mongolian Labor Law
(Хөдөлмөрийн тухай хууль), built for the legal staff of the Parliament
Secretariat (УИХ-ын Тамгын газар). `CLAUDE.md` is the product specification.

> The system proposes, legal staff decide. Every item is cited (law, provision,
> link); facts ("Баримт") and model suggestions ("Санал, 82%") are kept apart
> in data, API and UI; nothing is shown as a legal verdict.

## 1. What it does

Select a law or a provision and see, as grouped lists:

1. provisions that cite it — **Үүнийг иш татсан** (fact)
2. provisions it cites — **Үүнээс иш татсан** (fact)
3. citations that use a former law name — **Хуучин нэр** (fact, warning)
4. citations of provision numbers that no longer exist (old numbering, repealed) — **Заалт олдсонгүй** (fact, warning), with the current number when a renumbering table knows it
5. provisions regulating the same matter — **Ижил асуудлыг зохицуулсан** (suggestion, similarity score)
6. possible overlaps — **Болзошгүй давхардал** (suggestion)
7. possible conflicts — **Болзошгүй зөрчил** (suggestion), opened side by side with ILO / foreign sources and a resolution suggestion
8. international sources — **Олон улсын эх сурвалж** (curated ILO NORMLEX, EUR-Lex, legislation.gov.uk)

Plus:

- **Нөлөөллийн шинжилгээ** — edit a provision temporarily (text, renumber, or rename the law) and see direct (depth 1) and indirect (depth 2–3) impact with totals. Nothing is saved: *"Энэ нь түр тооцоолол бөгөөд хуульд өөрчлөлт оруулахгүй."*
- **Хуулийн төслүүд** — for a bill: the amended provisions (parsed from "…гэснийг …гэж өөрчилсүгэй" wording), the co-submitted bills, and every law whose provisions cite what the bill changes: **Тусгагдсан** (in the package), **Орхигдсон** (not in the package), **Шалгах шаардлагатай** (reached indirectly).
- **Search** by law name, former name, provision number and keyword (Mongolian suffixes stemmed).
- **CSV татах** on every list.

**How it differs from the existing government AI analyzer:** that system checks a single draft against the Constitution and scores drafting quality. LawLens answers a different question — *"if this labor-related provision changes, what else across the connected body of labor law could be affected?"* — with sources. It complements, not replaces, the existing system.

## 2. Problem and users

Every labor-related bill means hours of manual searching across laws; one missed
reference (a renamed law, a renumbered provision, a law missing from the
co-submitted package) creates an inconsistency. Primary users: Secretariat legal
staff reviewing bills; secondary: ministry lawyers drafting labor bills.

## 3. Architecture

```
legalinfo.mn / LawForum / ILO NORMLEX, EUR-Lex, legislation.gov.uk
        │  data/pipeline/sources.py  (LegalInfoSource, LawForumSource, ParliamentSource, ILODataSource; mock + real)
        ▼
parse_law.py (PDF) / app.parser.law_text (plain text)        structure: articles, parts, clauses
app.parser.references  + law_names.json registry            FACTS: citations, former names, old/missing numbers
app.parser.amendments                                        FACTS: bill operations (replace/insert/delete/repeal/rename)
app.ai.embeddings (BAAI/bge-m3 | offline demo-ngram-v1)       SUGGESTIONS: similar provisions
app.ai.relations  (Claude via Anthropic SDK | precomputed)   SUGGESTIONS: conflict / overlap / consistent + resolution
        │  data/pipeline/build.py
        ▼
data/processed/*.jsonl  (contract: contracts/data-format.md)   ← validated by scripts/validate_data.py
        │  app/graph/loader.py (parameterised UNWIND batches)
        ▼
Neo4j 5 + APOC  (schema: backend/app/graph/schema.cypher)      or the in-memory graph (MOCK=1 / GRAPH_BACKEND=memory)
        │  GraphStore interface: app/graph/neo4j_store.py | app/graph/memory.py
        ▼
FastAPI services (app/services/*)  →  /api/*  (contract: contracts/api.md)
        ▼
React + Vite + TypeScript + Tailwind + TanStack Query/Virtual  — grouped lists, formal style, no graph drawing
```

The parser and AI services live once in `backend/app/` and are shared by the
pipeline (`data/pipeline/_backend.py` puts them on the path).

## 4. Tech stack

| layer | technology |
|---|---|
| graph | Neo4j 5 Community + APOC, native vector index (1024-dim) |
| backend | Python 3.11, FastAPI, Pydantic v2, neo4j driver, pytest |
| data / AI | regex parser, requests, sentence-transformers (`BAAI/bge-m3`, configurable via `EMBED_MODEL`), Anthropic SDK (Claude, structured output, disk cache) |
| frontend | React 19, Vite 6, TypeScript, Tailwind 4, TanStack Query, TanStack Virtual, React Router |
| tests | pytest (+ Neo4j parity), Vitest + Testing Library, Playwright |
| infra | Docker Compose, GitHub Actions; Vercel (web) + Railway (API) |

## 5. Project structure

```
CLAUDE.md                 product spec (source of truth)
contracts/                api.md, data-format.md, fixtures/ (recorded responses) + fixtures/processed/ ([ЖИШЭЭ] dataset)
data/
  labor-2021.json         real Labor Law parsed from the legalinfo.mn PDF (parse_law.py)
  law_names.json          name registry: current / former / short names, aliases
  international/          curated sources.json + suggested links.json (real)
  fixtures/sample/        [ЖИШЭЭ] sample law texts, drafts, renumbering table, precomputed judgements
  processed/              REAL processed dataset (contract format)
  raw/                    downloaded source files (drafts/, laws/, lawforum/)
  pipeline/               build.py, from_lawgraph.py, sources.py, validate.py, schemas.py, ...
backend/app/
  main.py config.py deps.py
  schemas/api.py          API models (mirrored by web/src/types/api.ts)
  routers/                laws, articles, misc (health, impact, drafts, search, export)
  services/               law, impact, reference, similarity, international, draft, search, export
  graph/                  store.py (interface), memory.py, neo4j_store.py, loader.py, schema.cypher
  parser/                 names.py, references.py, law_text.py, amendments.py, normalize.py
  ai/                     embeddings.py, relations.py (LLMRelationService)
  mock/record.py          regenerates contracts/fixtures/*.json
backend/tests/            parser, services (graph queries, impact, gap, search, CSV), API, contracts, Neo4j parity
web/src/                  pages/ (Laws, ArticleView, Impact, Drafts), components/, hooks/, lib/, types/
web/tests, web/e2e        Vitest, Playwright demo flow
scripts/                  seed_demo.py, build_processed_data.py, validate_data.py
parse_law.py load_neo4j.py semantic_links.py extract_norms.py   exploration graph tools (section 16)
```

## 6. Setup (local, no Docker)

Python 3.11+ and Node 22+.

```bash
cp .env.example .env
make install        # .venv (backend + data deps), npm install, Playwright Chromium
make mock           # API on :8000, MOCK=1 ([ЖИШЭЭ] dataset, no Neo4j)
make web            # UI on http://localhost:5173 (proxies /api to :8000)
```

## 7. Docker

```bash
docker compose up --build        # demo: http://localhost:5173 , API http://localhost:8000/api/health
```

Services: `backend` (Python 3.11, FastAPI), `web` (built with Node + Vite, served by
nginx which proxies `/api` to `backend`), `neo4j` (Neo4j 5 Community + APOC, profile
`graph`). The default `docker compose up` needs no `.env`, no Neo4j and no network
after the images are built.

Real data through Neo4j:

```bash
# .env: NEO4J_PASSWORD=<8+ chars>
MOCK=0 docker compose --profile graph up --build
# backend waits for Neo4j, loads data/processed into the empty graph (SEED_ON_START=1)
# Neo4j browser: http://localhost:7475  (bolt on 7688)
```

## 8. MOCK mode

`MOCK=1` (default) serves the **[ЖИШЭЭ] sample dataset** in
`contracts/fixtures/processed/` with the in-memory graph: no Neo4j, no Anthropic
API, no internet. The same services that query Neo4j compute every response, so
every law/article/draft id works. The UI shows the banner *"ЖИШЭЭ ӨГӨГДӨЛ…"*;
responses carry `X-LawLens-Sample: true`.

## 9. Neo4j

Schema, constraints and indexes: `backend/app/graph/schema.cypher`
(Law, LawName, Article, Draft, Source, Suggestion; HAS_ARTICLE, PART_OF, KNOWN_AS,
REFERS_TO, SIMILAR_TO, CONFLICTS_WITH / OVERLAPS_WITH / CONSISTENT_WITH, TARGETS,
AMENDS, CO_SUBMITTED_FOR, RELEVANT_SOURCE, AMENDMENT_SUGGESTION; vector index
`article_embedding`).

```bash
make load                                                     # data/processed -> Neo4j (NEO4J_* from .env)
cd backend && python -m app.graph.loader ../contracts/fixtures/processed --reset   # sample graph
```

The loader refuses to write into a database holding the exploration graph
(`:LawNode`, built by `load_neo4j.py`): the two use the same labels with different
properties (CLAUDE.md §10), so they run as separate compose services.

## 10. Data pipeline

```bash
python scripts/build_processed_data.py            # real: data/labor-2021.json + law_names + international -> data/processed
python scripts/build_processed_data.py --embed-model --llm   # bge-m3 similarity + Claude judgements (cached)
python scripts/seed_demo.py                       # [ЖИШЭЭ] sample -> contracts/fixtures/processed + endpoint fixtures
python scripts/validate_data.py                   # schema + integrity of both datasets, non-zero exit on failure
python -m pipeline.sources lawforum --search Хөдөлмөр   # (from data/) LawForum bill metadata -> data/raw/lawforum
```

Validation checks: unique law / article ids, every article belongs to its law,
every reference resolves to an existing law (and article), missing targets are
flagged exactly when the number does not exist, facts have confidence 1.0,
suggestions name their model, https source URLs, no orphan relations, sample texts
labelled `[ЖИШЭЭ]`.

## 11. API

Full contract with examples: [`contracts/api.md`](contracts/api.md). Interactive
docs: http://localhost:8000/docs.

`GET /api/health`, `/api/laws`, `/api/laws/{law_id}`, `/api/laws/{law_id}/articles`,
`/api/laws/{law_id}/connections`, `/api/articles/{article_id}` (+ `/connections`,
`/impact` GET/POST, `/international`, `/amendment`, `/relations/{other_id}`),
`POST /api/impact`, `/api/drafts`, `/api/drafts/{id}`, `/api/drafts/{id}/gaps`,
`/api/search?q=`, `/api/export?kind=…`.

## 12. Testing

```bash
make test                 # backend pytest, data pytest, web typecheck + Vitest + build, data validation
make e2e                  # Playwright: search → article → connections → comparison → impact → draft gap → CSV
cd web && E2E_BASE_URL=http://localhost:5173 npx playwright test     # same test against docker compose
NEO4J_TEST_URI=bolt://localhost:17687 NEO4J_TEST_PASSWORD=... make test-backend   # + Neo4j parity (disposable DB!)
```

CI (`.github/workflows/ci.yml`) runs all of this, including the Neo4j parity tests
against a Neo4j service container and a check that `seed_demo.py` reproduces the
committed fixtures.

## 13. Demo (3 minutes, on the [ЖИШЭЭ] dataset)

1. **Problem.** Open http://localhost:5173/laws — *"Хөдөлмөрийн тухай хуультай холбоотой бүх заалтыг нэг дор харуулна."*
2. **Connections.** Choose *Хөдөлмөрийн тухай хууль* → *80 дугаар зүйл. Ажлын цаг*. Show: Үүнийг иш татсан (Зөрчлийн тухай хууль 6.1 …), Үүнээс иш татсан, **Хуучин нэр** (80.3 cites "Хөдөлмөр хамгааллын тухай хууль"), **Заалт олдсонгүй** (Зөрчлийн тухай хууль 6.4 cites 80.5), Ижил асуудлыг зохицуулсан (Санал, 96%).
3. **Impact.** Click *Нөлөөллийн шинжилгээ хийх* (or the menu), choose 80.1, change "40" to "38", press **Нөлөөллийг тооцоолох**: depth 1 = 4 provisions, depth 2 = 2, total 6 provisions in 4 laws.
4. **Draft gap.** *Хуулийн төслүүд* → *[ЖИШЭЭ] Хөдөлмөрийн тухай хуульд нэмэлт, өөрчлөлт…*: Зөрчлийн тухай хууль **Тусгагдсан**; Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хууль and Хөдөлмөрийн хөлсний доод хэмжээний тухай хууль **Орхигдсон**; Нийгмийн даатгалын тухай хууль **Шалгах шаардлагатай**. Click **CSV татах**.
5. **Suggested conflict.** Back on article 80 → *7. Болзошгүй зөрчил* → **Харьцуулах**: 80.1 (40 цаг) vs ХАБЭА 12.1 (48 цаг) side by side, explanation, ILO C001 / EU 2003/88/EC / UK WTR 1998, resolution suggestion — all marked *Санал* and *Шалгах шаардлагатай*.
6. **Close.** *"Одоо байгаа AI систем нь төслийг Үндсэн хуультай харьцуулан шалгадаг. LawLens нь төсөл хөдөлмөрийн эрх зүйн бусад зохицуулалтад ямар нөлөө үзүүлэхийг эх сурвалжтайгаар харуулна."*

To show the **real** Labor Law instead: `make real` (in-memory)
(or the Neo4j compose profile) — see "Data" below for what it contains.

## 14. Data: real vs [ЖИШЭЭ]

| data | status |
|---|---|
| Хөдөлмөрийн тухай хууль (2021 revised), 1,155 articles/parts/clauses, from the legalinfo.mn PDF | **real** (`data/processed`) |
| 246 citations from the real Labor Law (208 internal, 38 to 17 other laws) | **real facts**, regex; the new extractor agrees 208/208 with `parse_law.py` on internal citations |
| Old-name / missing-target findings in the real data | **0 found** — the texts of the citing laws are not loaded yet, so the headline hypothesis is not yet tested on real data |
| Other laws' texts, their citations of the Labor Law, similarity, relations, drafts, renumbering table, former names used in the demo | **[ЖИШЭЭ]** invented (`data/fixtures/sample`, `contracts/fixtures/processed`) |
| International sources (10: ILO C001/C111/C131/C155, EU 2003/88, 2022/2041, 89/391, UK WTR 1998, NMWA 1998, Equality Act s.13) | **real documents**, hand-curated summaries; links to real Labor Law articles are model suggestions (`claude-opus-5-5`); links in the sample are [ЖИШЭЭ] |
| Relation judgements in the demo | **precomputed** [ЖИШЭЭ] (`demo-llm`) or rule-based (`demo-heuristic`) |

External services: **connected (tested live)** — LawForum public API (bill metadata).
**Adapters, not used by the demo** — legalinfo.mn download, Parliament API (needs
credentials), Anthropic (needs `ANTHROPIC_API_KEY`), sentence-transformers bge-m3.
**Mocked** — all of them in `MOCK=1`.

## 15. Limitations

- No precision measurement on a gold set yet (CLAUDE.md §15 asks ≥ 95%); the only measured number is the 208/208 agreement between two independent extractors on internal references.
- Only the Labor Law text is loaded; citing laws are known by name only, so reverse citations, old names and missing targets across laws are demonstrated on [ЖИШЭЭ] data.
- LawForum's public API gives bill metadata only (no text, no co-submitted list); real bills must be added to `data/raw/drafts/*.json` with their text.
- ILO NORMLEX pages sit behind a browser challenge and could not be link-checked by script (EUR-Lex and legislation.gov.uk were).
- Offline similarity (`demo-ngram-v1`) is lexical; use `--embed-model` (bge-m3) for real semantic similarity. Relation judgements without an API key are precomputed or rule-based.
- Impact follows citations only (not unreferenced semantic dependencies, which appear as similarity suggestions); depth 2+ follows citations of the depth-1 provision or its containing article/part.
- Name-only laws link to the legalinfo.mn home page until their exact URL is recorded in `law_names.json`.

## 16. Real-data integration roadmap

1. Download the texts of the connected laws (seed list in CLAUDE.md §4) from legalinfo.mn → `parse_law.py` → add to `PARSED` in `scripts/build_processed_data.py`; verify current / former names in `data/law_names.json`.
2. Rebuild: reverse citations, old names and missing numbers across laws then come from real data — the headline check.
3. Add the correspondence table of the 2021 revision (old → new numbers) to populate `current_number`.
4. Build a gold set (≈200 citations), measure precision/recall, report it.
5. Real bills: LawForum metadata (`pipeline.sources lawforum`) + bill texts into `data/raw/drafts/`.
6. `--embed-model --llm` for similarity and Claude judgements (cached in `data/cache/llm`), review before publishing.
7. Curate more ILO / foreign sources (NATLEX list of conventions ratified by Mongolia, opened by a person).

## 17. Deployment

- **web → Vercel.** Root directory `web`, preset Vite, build `npm run build`, output `dist` (`web/vercel.json` adds the SPA rewrite). Env `VITE_API_BASE=https://<api domain>` (no trailing slash).
- **API → Railway.** `railway.json` builds `backend/Dockerfile.railway` (ships `contracts/` and `data/processed/`), health check `/api/health`, `MOCK=1` for the sample demo; `MOCK=0` + `GRAPH_BACKEND=memory` serves the real data without a database, or `GRAPH_BACKEND=neo4j` with `NEO4J_*` (Railway Neo4j / AuraDB) after `python -m app.graph.loader`.
- Restrict `CORS_ORIGINS` to the Vercel domain before a public launch. Secrets only in `.env` / platform settings.

---

## LawGraph: exploration graph tools (Монгол)

Монгол Улсын хуулийн PDF-ээс **мэдлэгийн граф** үүсгэж, судалгаа/GraphRAG-д зориулсан тусдаа Neo4j-д ачаалдаг хэрэгсэл. API-ийн графаас тусдаа (`:LawNode` шошго, `uid`), тиймээс өөр Neo4j контейнерт ажиллана.

```bash
./build.sh                                   # neo4j-explore асаах → PDF задлах → граф ачаалах → data/processed
./build.sh path/to/law.pdf other-law-id      # өөр хууль нэмэх
```

- Neo4j Browser: http://localhost:7474 (`docker compose --profile explore up -d neo4j-explore`)
- Жишээ асуулгууд: [`queries.cypher`](queries.cypher)

| Файл | Үүрэг |
|---|---|
| `parse_law.py` | PDF → `data/<id>.json` (бүтэц, ишлэл, нэр томьёо, оролцогч, нэмэлт өөрчлөлт) |
| `load_neo4j.py` | JSON → Neo4j (`--reset` өмнөх өгөгдлийг устгана) |
| `semantic_links.py` | Embedding (`multilingual-e5-large`, локал) → `SIMILAR_TO`, `RELATED_TO`, `:Topic` |
| `extract_norms.py` | Claude API → `:Norm` (хэн → эрх/үүрэг → юу), ишлэлийн утгын үүрэг |

Одоогийн үр дүн (Хөдөлмөрийн тухай хууль): 13 бүлэг · 17 дэд бүлэг · 166 зүйл · 615 хэсэг · 375 заалт · 146 дотоод ишлэл · 18 гадны хууль · 17 нэр томьёо · 47 нэмэлт/өөрчлөлтийн тэмдэглэл.

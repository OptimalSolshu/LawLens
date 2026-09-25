# CLAUDE.md — LawLens project context

Read this file fully before doing any work in this repository. It is the single
source of truth for what we are building, why, for whom, and how. If a request
conflicts with this file, point out the conflict and ask before proceeding.

---

## 1. One-sentence summary

LawLens is a knowledge graph of the Mongolian Labor Law (Хөдөлмөрийн тухай
хууль) and every law connected to it. Selecting a provision shows, as simple
grouped lists, every law and provision that references it, that it references,
or that regulates the same matter; editing a provision shows its impact (but
the system does not apply or save any edits: impact is computed with Neo4j
queries, so we can see what else WOULD change IF a change were made —
NECESSARY); and possible overlaps (in legal logic) and conflicts (in legal
logic) are shown with international labor standards and foreign examples as
reliable, cited reference material.

If a conflict exists, suggest possible ways to resolve it based on reliable
foreign examples (optional).

---

## 2. Context

- Team: 3 developers, building with Claude Code, repository on GitHub.
- The organisers and judges are the same people who would use the product:
  legal staff of the Parliament Secretariat (УИХ-ын Тамгын газар).
- The government already has an AI analyzer. It checks a single draft against
  the Constitution (mainly Article 16, human rights) and scores regulatory
  quality (vague wording, missing deadlines, missing responsible party). It
  also only shows the NUMBER of related laws, not which laws they are. It does
  NOT look across other laws. LawLens complements it; it does not compete with
  it and does not repeat its checks.

---

## 3. The problem

When a bill is submitted, Secretariat legal staff review it with a manual
checklist. According to our mentors they:

1. Study related laws and their connections.
2. Check conflicts with other laws: not only the Constitution, but organic
   laws, laws of other sectors, and international treaties and conventions.
3. Count how many laws reference the same matter and which provisions are
   affected.
4. Assess budget pressure of the change.
5. Do international comparative research.
6. Write a short explanation of what the change brings (to be handled with
   Claude LLM).
7. Suggest ways to avoid conflicts (to be handled with Claude LLM).

All of this is done by searching laws by hand. It is slow, depends on the
experience of the person, and mistakes are easy.

### Mentor tips (must shape every design decision)

- _Renames and restructuring (VERY IMPORTANT)._ Laws get renamed (example:
  "Зөвшөөрлийн тухай хууль" → "Зөвшөөрөл, мэдэгдлийн тухай хууль") and fully
  revised (шинэчилсэн найруулга), which renumbers provisions. Every provision
  in other laws that still uses an old name or an old provision number must be
  found.
- _Frequently changed laws._ "Зөрчлийн тухай хууль" (Law on Infringements)
  changes very often and is referenced by many laws, including for sanctions on
  labor violations. Impact analysis must be complete and fast. (For now we do
  not cover all laws; we implement only the Labor Law.)
- _Conflicts beyond the Constitution._ Check organic laws, other sectors,
  and international treaties/conventions (from reliable sources only).
- _Co-submitted bills._ A bill comes with amendment bills to other laws.
  Laws that should have been amended but are missing from the package are a
  real, recurring problem.
- _Reliable sources._ Every statement must be traceable to an exact law,
  provision number, and link. Staff will not trust unsourced AI opinions.
- _Suggest, do not decide._ The system proposes; legal staff decide.

---

## 4. Scope

### In scope: the Labor Law and everything connected to it

Center: Хөдөлмөрийн тухай хууль (the current revised version; verify the
adoption date, effective date, and current text on legalinfo.mn).

Connected laws: discovered automatically by the graph, starting from this seed
list (verify exact current names on legalinfo.mn):

- Нийгмийн даатгалын тухай хууль and related social insurance laws
- Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн тухай хууль
- Хөдөлмөрийн хөлсний доод хэмжээний тухай хууль
- Хөдөлмөр эрхлэлтийг дэмжих тухай хууль
- Зөрчлийн тухай хууль (sanctions for labor violations)
- Иргэний хууль
- Төрийн албаны тухай хууль
- Laws on labor migration and employment of foreign citizens
- Every other law that references the Labor Law (found by the pipeline)

International: ILO conventions ratified by Mongolia (list taken from ILO
NATLEX / NORMLEX, never from memory) and selected foreign labor laws for
comparison.

Demo scenario: the revised Labor Law renumbered provisions. Hypothesis to
verify with real data: some provisions in other laws may still cite the old
Labor Law or old provision numbers. If true, this is the headline finding of
the demo. If false, say so honestly and use the next-best real finding.

### Out of scope (do not build)

- Implementation tracking of secondary regulations, reminders, monthly
  reports, n8n or other workflow automation.
- Graph visualizations (no node-link diagrams in the UI).
- Budget calculations (at most flag provisions that create new bodies,
  positions, or payments, as suggestions).
- Laws unrelated to labor.
- Legal advice to citizens.

---

## 5. Users

- Primary: Parliament Secretariat legal staff reviewing labor-related bills.
- Secondary: ministry lawyers drafting labor bills who want to check before
  submitting.
- Later: the public (not in the hackathon).

---

## 6. Features

1. _Connections of a provision or law._ Grouped lists:
   - laws/provisions that reference it (fact),
   - laws/provisions it references (fact),
   - references that use a former name or old numbering (warning),
   - references to provisions that do not exist in the target law (warning),
   - provisions regulating the same matter without a direct reference
     (suggestion, similarity score),
   - possible overlaps or conflicts (suggestion, explanation).
2. _Impact analysis._ Edit a provision's text, or rename/renumber a law,
   and see every affected provision grouped by depth: direct references
   (depth 1) and indirect (depth 2), with totals.
3. _Former-name and old-number detection._ Resolve former names, short
   names, and old numbering to the right law; flag every outdated reference
   (detect only, do not modify).
4. _Overlap and conflict suggestions._ Similar provisions across laws
   (embeddings), classified by an LLM as conflict / overlap / consistent,
   always with both provisions shown side by side and an explanation.
5. _International reference._ For a flagged provision: relevant ILO
   convention provisions and foreign labor law examples, each from a curated,
   cited source.
6. _Export._ Any list to CSV.

---

## 7. Principles (non-negotiable)

- _Every item is cited:_ law name, provision number, source URL.
- _Facts and suggestions are separate_ in data, API, and UI.
  Facts: references found by deterministic parsing (confidence 1.0).
  Suggestions: embeddings and LLM outputs, with confidence and model name.
- _Never invent legal content._ Any sample or test data is labelled
  "[ЖИШЭЭ]" (sample; fixtures carry `"_sample": true`) and never shown as real.
- _Only curated international sources._ No unsourced web claims.
- _The system does not decide._ Wording in UI and outputs: "санал",
  "шалгах шаардлагатай", never "зөрчилтэй" as a final verdict.
- _Online demo_: frontend on Vercel, backend on Railway (see "Deployment").

Signal the tech at the core of your build.
Claim your .tech domain, sponsored for 1 year.

- _No secrets in code._ Everything from .env.

---

## 8. Data sources

| Source                                                          | What we take                                                                                                                           |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| legalinfo.mn                                                    | Full text of the revised Labor Law (https://legalinfo.mn/mn/detail?lawId=16230709635751) and connected laws, former names, source URLs |
| LawForum API (https://lawforum.parliament.mn/LawForumAPI/docs/) | Labor-related bills, details, co-submitted bills (verify availability)                                                                 |
| Parliament API (http://202.21.104.13/ParliamentAPI/docs/)       | Agenda, meetings, vote results for bills (optional context)                                                                            |
| ILO NATLEX / NORMLEX                                            | Conventions ratified by Mongolia, foreign labor laws                                                                                   |
| legislation.gov.uk, EUR-Lex                                     | Selected comparative examples (curated)                                                                                                |

Parliament API: POST /api/login returns a bearer token; functions via
POST /ParliamentService with {"func": ...} (getAgendaList,
getAgendaVoteList, getMeetings, getVotingList, getVotingResult).
Credentials come from .env (PARLIAMENT_USER, PARLIAMENT_PASS).

---

## 9. Mongolian legal text rules

- Article heading: "12 дугаар зүйл. Гарчиг" or "12 дүгээр зүйл".
- Clauses at line start: "12.1.", "12.3.1.".
- Reference forms to support:
  "…тухай хуулийн 15.1-д", "…тухай хуулийн 6 дугаар зүйлийн 8 дахь хэсэгт",
  "…тухай хуулийн 12 дугаар зүйлд", "энэ хуулийн 5.3-т", "Иргэний хуулийн …".
- Case endings: хууль / хуулийн / хуулиар / хуульд / хуулийг.
- Locatives: дахь / дэх / дох / дөх.
- Match longer law names before shorter names that are substrings.
- Former and short names resolve to the same law (law_names.json).
- If the cited number does not exist in the target law, keep the reference,
  link it to the law, and set target_missing = true.
- Amendment wording: "…гэснийг …гэж өөрчилсүгэй", "…гэсний дараа …гэж
  нэмсүгэй", "…гэснийг хассугай".

---

## 10. Architecture and tech stack

```
legalinfo.mn / LawForum / NATLEX
        ↓
parse_law.py (Python)    PDF → data/<law_id>.json: structure, references
                         (regex, fact), terms, actors, amendments
data/pipeline            from_lawgraph → processed/laws.jsonl, refs.jsonl
                         → embeddings (multilingual-e5-large) → similar (suggestion)
                         → Claude: relations, international links,
                           amendment suggestions (cached)
        ↓  data/processed/*.jsonl  (contract)
backend (FastAPI)        loads into Neo4j knowledge graph, Cypher queries
        ↓  /api/*  (contract)
web (React)              grouped, scrollable lists in formal gov style
```

| Layer           | Technology                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------ |
| Knowledge graph | Neo4j 5 Community + APOC, native vector index                                              |
| Backend         | Python 3.11, FastAPI, pydantic v2, neo4j driver, pytest                                    |
| Data / AI       | requests, regex, fastembed / sentence-transformers (intfloat/multilingual-e5-large, 1024-dim, configurable), Anthropic SDK (Claude) |
| Frontend        | React + Vite + TypeScript + Tailwind + TanStack Virtual + TanStack Query                   |
| Infra           | Docker Compose (local), Vercel (web), Railway (API), GitHub (private), GitHub Actions (tests + build) |

### Graph model

Source of truth: `backend/app/graph/schema.cypher`. If this section and that
file disagree, the file wins.

Nodes: Law {law_id, name, former_names[], short_names[], adopted_date,
source_url}, Article {article_id, law_id, number, parent_number, title, text,
embedding}, Draft, IntlSource (foreign law or treaty), Suggestion.
Relationships:

- Law-HAS_ARTICLE->Article, Article-CHILD_OF->Article
- Former/short names are properties of Law (`former_names`), not nodes.
- Fact: Article-REFERS_TO->Article {raw_text, matched_name, uses_old_name,
  method, confidence}
- Fact: Article-REFERS_TO_MISSING->Law {to_number, raw_text, matched_name,
  uses_old_name, method, confidence} (target provision does not exist)
- Suggestion: Article-SIMILAR->Article {score, model} (stored once, query
  undirected)
- Suggestion: Article-RELATION->Article {kind: conflict|overlap|consistent,
  confidence, explanation, model}
- Draft-TARGETS->Law, Draft-AMENDS->Article, Draft-COSUBMITS->Law
- Article-INTL_LINK->IntlSource {relevance, explanation}
- Article-AMENDMENT_SUGGESTION->Suggestion {reason, suggested_text,
  based_on_source_ids[], model}

IDs (from our pipeline):
- law_id: stable ASCII slug. A parsed law keeps its `parse_law.py --id`
  (e.g. `labor-2021`), so it survives renames. A law known only by name gets
  `pipeline.ids.law_id(name)`.
- article_id: `{law_id}:{number}`, e.g. `labor-2021:80.1.4`. Same as the
  `uid` that `load_neo4j.py` uses.

`load_neo4j.py`, `semantic_links.py` and `extract_norms.py` build a richer
local graph (Chapter, Section, Provision, Term, Actor, Norm, Topic) for
exploration and GraphRAG. It uses the same `:Law` and `:Article` labels with
different properties, so do not load it into the Neo4j database that the API
uses.

### Contracts

- contracts/data-format.md: files in data/processed/ (laws.jsonl,
  refs.jsonl, similar.jsonl, relations.jsonl, drafts.json,
  international.json, amendments.jsonl).
- contracts/api.md: every endpoint with example JSON; common shapes
  RefItem and LawGroup; every item has law name, provision number,
  source_url, type fact|suggestion, confidence, flags.
- contracts/fixtures/: formal Mongolian SAMPLE data for every endpoint; the
  backend serves them when MOCK=1.
- Contracts change only by agreement of all three members.

### Deployment

One repository with two deploy targets. You do not need separate projects or
repositories for the backend and the frontend.

- **web → Vercel.** Project Root Directory `web`, framework preset Vite,
  build `npm run build`, output `dist`. Env: `VITE_API_BASE=https://<railway
  domain>` (no trailing slash).
- **backend → Railway.** Service from this repo with Root Directory left at
  the repo root. `railway.json` builds `backend/Dockerfile.railway`, which
  ships `contracts/` and `data/processed/` in the image and listens on
  `$PORT`. Health check: `/api/health`. Env: `MOCK=1` until the graph
  queries exist; for `MOCK=0` also set `NEO4J_URI`, `NEO4J_USER`,
  `NEO4J_PASSWORD` (a Neo4j service on Railway, or Neo4j AuraDB).
- CORS is open (`allow_origins=["*"]`). Restrict it to the Vercel domain
  before a public launch.
- **Offline demo fallback:** `docker compose up` runs the same stack locally
  from precomputed data.

---

## 11. UI rules

- Formal government tool. Follow the look of https://lawforum.parliament.mn/:
  plain header with system name, short text menu, white content, simple
  lists, plain footer "Монгол Улсын Их Хурал".
- System name: "Хуулийн уялдааны шинжилгээ" (small "LawLens" allowed).
- No emoji, no gradients, shadows, illustrations, playful copy, or branding.
- One accent color (reuse lawforum's). Status via plain text labels:
  "Баримт", "Санал, 82%", "Хуучин нэр", "Заалт олдсонгүй", "Орхигдсон",
  "Тусгагдсан".
- Lists only, no graph visualization. Two columns: search/selection left,
  results right. Menu: "Хууль хайх", "Нөлөөллийн шинжилгээ",
  "Хуулийн төслүүд".
- Formal Mongolian wording; readable on a projector (15–16px base).

---

## 14. Demo (3 minutes)

1. Problem in the mentors' words: every labor bill means hours of manual
   searching across laws; one missed reference creates a legal conflict.
2. Select a Labor Law provision: grouped lists of every connected provision
   with sources.
3. Old names and numbers: provisions in other laws still citing outdated
   references (real numbers from our data).
4. Co-submitted gap: a real labor bill from LawForum → laws missing from the
   package.
5. Conflict suggestion → ILO convention and a foreign example → amendment
   suggestion, clearly marked as needing review.
6. Close: "The existing AI checks a draft against the Constitution. LawLens
   shows what the draft does to the whole body of labor law, with sources."
   (Staff make the decision — this is outside the system's role.)

Use only real numbers from our data in the demo. State measured accuracy.

---

## 15. Definition of done

- The Labor Law and its connected laws are loaded; references have measured
  precision ≥ 95% on the gold set.
- Every API response matches contracts/api.md; tests pass in CI.
- UI shows connections, impact, former-name/old-number warnings, and the
  co-submitted gap on real data, in the formal style, with no emoji.
- Every item has a working source link; facts and suggestions are visually
  distinct.
- The demo runs fully offline from precomputed data.

---

## 16. Glossary

| Mongolian                          | Meaning in this project                     |
| ---------------------------------- | ------------------------------------------- |
| Хөдөлмөрийн тухай хууль            | Labor Law, the center of our scope          |
| зүйл / хэсэг / заалт               | article / part / clause (provision)         |
| ишлэл, иш татах                    | reference, to reference                     |
| шинэчилсэн найруулга               | full revised version (renumbers provisions) |
| нэмэлт, өөрчлөлт                   | amendment                                   |
| хамт өргөн мэдүүлсэн төсөл         | bills co-submitted with the main bill       |
| үзэл баримтлал                     | concept paper of a bill                     |
| хүчингүй болсон                    | repealed                                    |
| зөрчил / давхардал / нийцэл        | conflict / overlap / consistency            |
| Баримт / Санал                     | fact / suggestion (UI labels)               |
| ОУХБ                               | International Labour Organization (ILO)     |
| Эрх зүйн мэдээллийн нэгдсэн систем | legalinfo.mn                                |

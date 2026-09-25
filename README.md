# LawGraph

Монгол Улсын хуулийн PDF-ээс **мэдлэгийн граф (knowledge graph)** үүсгэж, Neo4j-д ачаалдаг хэрэгсэл.
Одоогоор **Хөдөлмөрийн тухай хууль (2021, шинэчилсэн найруулга)** ачаалагдсан.

## Эхлүүлэх

```bash
./build.sh                                   # Neo4j асаах → PDF задлах → граф ачаалах
./build.sh path/to/law.pdf other-law-id      # өөр хууль нэмэх
```

- Neo4j Browser: http://localhost:7474 (нэвтрэх нэр `neo4j`, нууц үг `.env` файлд байгаа)
- Bolt: `bolt://localhost:7687`
- Жишээ асуулгууд: [`queries.cypher`](queries.cypher)

## Бүтэц

| Файл | Үүрэг |
|---|---|
| `docker-compose.yml` | Neo4j 5 Community + APOC (зөвхөн localhost дээр), `api`, `web` (`build.sh` зөвхөн `neo4j`-г асаана) |
| `parse_law.py` | PDF → `data/<id>.json` (бүтэц, ишлэл, нэр томьёо, оролцогч, нэмэлт өөрчлөлт) |
| `load_neo4j.py` | JSON → Neo4j (`--reset` өмнөх өгөгдлийг устгана) |
| `semantic_links.py` | Embedding (`multilingual-e5-large`, локал) → `SIMILAR_TO`, `RELATED_TO`, `:Topic`, вектор индекс |
| `extract_norms.py` | Claude API → `:Norm` (хэн → эрх/үүрэг → юу → хэний өмнө), ишлэлийн утгын үүрэг (`ANTHROPIC_API_KEY` шаардлагатай) |
| `queries.cypher` | Жишээ Cypher асуулгууд, GraphRAG context авах асуулга |

## Графын загвар (ontology)

```
(:Law)-[:HAS_CHAPTER]->(:Chapter)-[:HAS_SECTION]->(:Section)-[:HAS_ARTICLE]->(:Article)
                         (:Chapter)-[:HAS_ARTICLE]->(:Article)            // дэд бүлэггүй бол
(:Article)-[:HAS_PROVISION]->(:Provision:Part)-[:HAS_PROVISION]->(:Provision:Point)
(:Article)-[:NEXT]->(:Article)

(:Provision)-[:REFERS_TO]->(:Provision | :Article | :Chapter)   // "энэ хуулийн 80.1-д заасан"
(:Provision)-[:CITES]->(:ExternalLaw)                           // "Зөрчлийн тухай хууль"
(:Provision)-[:MENTIONS]->(:Term | :Actor)
(:Term)-[:DEFINED_IN]->(:Provision)                             // 4.1.x нэр томьёо
(:Provision | :Article)-[:AMENDED_BY {type}]->(:AmendingLaw {date})

// утгын давхарга
(:Provision)-[:SIMILAR_TO {score}]->(:Provision)                // embedding, өөр зүйлийн ойр заалт
(:Article)-[:RELATED_TO {score}]->(:Article)
(:Provision | :Article)-[:ABOUT]->(:Topic)                      // k-means сэдэв
(:Actor)-[:HAS_RIGHT|HAS_DUTY|IS_PROHIBITED|HAS_POWER|IS_LIABLE]->(:Norm)-[:TOWARDS]->(:Actor)
(:Norm)-[:STATED_IN]->(:Provision)
(:Provision)-[:REFERS_TO {role}]->()                            // үл хамаарах / нөхцөл / журам ...
```

| Шошго | Тайлбар |
|---|---|
| `Provision` | `number` (жишээ `80.1.4`), `text`, `level` (1 = хэсэг `:Part`, 2 = заалт `:Point`), `status` (хүчинтэй/хүчингүй), `modality` (эрх / үүрэг / хориглол / хариуцлага) |
| `Term` | 4 дүгээр зүйлд тодорхойлсон 17 нэр томьёо + тодорхойлолт. Ажил олгогч, ажилтан гэх мэт талууд нь мөн `:Actor` шошготой |
| `Actor` | Засгийн газар, шүүх, арбитр, улсын байцаагч, жирэмсэн эмэгтэй гэх мэт оролцогч, бүлэг (`category`-тай) |

Бүх хуулийн доторх зангилаа `:LawNode` шошготой, `uid = "<law_id>:<id>"` (жишээ `labor-2021:80.1.4`) тул олон хуулийг нэг графд зэрэг хадгалж болно.

## Одоогийн үр дүн (Хөдөлмөрийн тухай хууль)

13 бүлэг · 17 дэд бүлэг · 166 зүйл · 615 хэсэг · 375 заалт · 146 дотоод ишлэл · 18 гадны хууль · 17 нэр томьёо · 47 нэмэлт/өөрчлөлтийн тэмдэглэл

## Хязгаарлалт

- Нэр томьёо, оролцогчийг **дүрэм (regex) болон үгийн үндсээр** тааруулсан. Монгол хэлний тийн ялгалын бүх хувилбарыг барихгүй байж магадгүй.
- `modality` нь түлхүүр үгэнд суурилсан ("хориглоно", "эрхтэй", "болно", "үүрэгтэй").
- Дараагийн алхам: LLM-ээр семантик triple гаргах (хэн → ямар үүрэгтэй → хэний өмнө), embedding нэмж GraphRAG болгох.

---

## LawLens апп (backend + web)


Knowledge graph of Mongolian legislation for the Parliament Secretariat
(Тамгын газар). Pick a law or provision to see every connected law and
provision as grouped lists. Edit a provision or rename a law to see the
ripple effect. It also detects references that use a law's former name,
references to missing or repealed provisions, laws missing from a bill's
co-submitted package, similar provisions, and possible conflicts, with
international examples and amendment suggestions.

**Scope is only this knowledge graph.** No implementation tracking,
reminders, reports, n8n, or graph visualization.

### Setup

```bash
cp .env.example .env          # fill in secrets; .env is never committed
docker compose up -d --build  # or: make up
```

| service | url |
|---|---|
| web (Vite) | http://localhost:5173 |
| api (FastAPI, `/docs`) | http://localhost:8000 |
| Neo4j browser | http://localhost:7474 |

`MOCK=1` (default) makes the API serve `contracts/fixtures/` so nobody waits
on Neo4j or data. Set `MOCK=0` once the loader and queries exist.

Without Docker (Python 3.11+, Node 22):

```bash
make install   # .venv + npm install
make mock      # API on :8000 from fixtures
make web       # UI on :5173, /api proxied to :8000
make test      # backend + data pytest   (make test-web = tsc + vite build)
make validate-data   # check data/processed against the contract
make load      # data/processed -> Neo4j
```

### Team ownership

| area | owner | works in |
|---|---|---|
| graph + API | member 1 | `backend/`: `app/graph/queries.py`, `loader.py`, `schema.cypher` |
| UI | member 2 | `web/`: pages built on `src/api.ts` + `src/types.ts` |
| data + AI | member 3 | `data/`: `pipeline/*`, `raw/laws/`, `law_names.json`, `processed/` |

Shared: `contracts/` (everyone reads, nobody edits alone).

### Rules

- **`contracts/` changes only via PR reviewed by all three.** A contract
  change updates, in the same PR: the markdown, `backend/app/models.py`,
  `web/src/types.ts`, `data/pipeline/schemas.py` (if data format), and the
  fixtures. CI fails if fixtures drift from the models.
- Branch per member: `m1-backend`, `m2-web`, `m3-data`. Rebase on `main` often.
- **Merge to `main` at hour 8 and hour 14.** CI must be green.
- Secrets only in `.env`.
- Reliability: every result cites law + provision + link. `type: "fact"`
  (parsed/regex/name history) and `type: "suggestion"` (embeddings/LLM) are
  always shown separately, with confidence.
- Fixtures are invented SAMPLE data (`"_sample": true`, texts prefixed
  `[ЖИШЭЭ]`, links to example.org). Never present them as real law.

### IDs

- `law_id`: ASCII slug of the **current** name, via `data/pipeline/ids.py`
  (`Зөвшөөрлийн тухай хууль` → `zovshoorliin-tukhai-khuuli`).
- `article_id`: `{law_id}:{number}` → `zovshoorliin-tukhai-khuuli:15.1`.

### Layout

```
contracts/     api.md, data-format.md, fixtures/ (per endpoint + processed/ samples)
data/          pipeline/ (scrape, parser, references, embeddings, llm, validate), raw/laws/, processed/
backend/       app/main.py, app/models.py, app/graph/ (driver, schema.cypher, loader, queries)
web/           src/types.ts, src/api.ts, src/App.tsx (placeholder law list)
```

### Notes on the replaced starter

The earlier PostgreSQL starter (`schema.sql`, `load.py`, `api.py`) is
replaced by Neo4j + FastAPI. Its `parser.py` and `references.py` were meant to
move to `data/pipeline/`, but they were not in the folder when this scaffold
was created. Stub modules with the target signatures are in place. Member 3:
drop the starter code into those files and adapt the output to
`contracts/data-format.md`.

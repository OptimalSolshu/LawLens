# data/

| path | what | real / sample |
|---|---|---|
| `labor_law_2021.pdf`, `labor-2021.json` | Хөдөлмөрийн тухай хууль (2021 revised) from legalinfo.mn, parsed by `../parse_law.py` | real |
| `law_names.json` | name registry: `current_name`, `former_names`, `short_names`, `aliases` (contracts/data-format.md) | real names as cited; add former names only after checking legalinfo.mn |
| `international/sources.json` | curated ILO / EU / UK sources (opened by a person) | real documents |
| `international/links.json` | suggested links between real Labor Law articles and those sources (`model` set) | suggestions |
| `processed/` | the real processed dataset served with `MOCK=0` | real |
| `raw/` | downloads: `laws/*.pdf`, `drafts/*.json` (bills with text), `lawforum/` (API metadata) | real, not committed when large |
| `fixtures/sample/` | **[ЖИШЭЭ]** invented law texts (`laws/*.txt`), bills (`drafts/*.json`), renumbering table, precomputed relation judgements, sample links | invented, never real law |
| `pipeline/` | build.py (dataset builder), from_lawgraph.py, sources.py (adapters), validate.py, schemas.py | code |

Every sample provision text starts with `[ЖИШЭЭ]`; sample records carry `"_sample": true`
and link to `https://example.org/lawlens-sample/...`.

## Commands (from the repo root)

```bash
python scripts/build_processed_data.py     # data/processed from real inputs
python scripts/seed_demo.py                # contracts/fixtures/processed from fixtures/sample + endpoint fixtures
python scripts/validate_data.py            # both datasets; exit 1 on any problem
cd data && pytest -q                       # pipeline tests
```

## Adding a real law

1. Save the PDF from legalinfo.mn to `raw/laws/<law_id>.pdf`.
2. `python ../parse_law.py raw/laws/<law_id>.pdf --id <law_id> -o <law_id>.json`
3. Add it to `PARSED` in `scripts/build_processed_data.py` with its legalinfo.mn URL.
4. Record verified former / short names in `law_names.json`.
5. Rebuild and validate.

## Adding a real bill

Create `raw/drafts/<lawforum_id>.json` (same shape as `fixtures/sample/drafts/*.json`):
`{lawforum_id, title, source_url, text, cosubmitted: [{title, text}]}`. The text is
parsed for amendment wording ("…гэснийг …гэж өөрчилсүгэй", "…гэсний дараа …гэж
нэмсүгэй", "…гэснийг хассугай", "…хүчингүй болсонд тооцсугай", "…нэрийг …гэж
өөрчилсүгэй"). `python -m pipeline.sources lawforum --search …` fetches bill metadata
(the public LawForum API has no bill text).

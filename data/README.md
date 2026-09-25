# data/

| path | what | real / sample |
|---|---|---|
| `legalinfo_catalog.json` | the laws we parse: legalinfo.mn lawId of the text in force, name, law_id | real |
| `<law_id>.json` | each catalog law parsed by `../parse_law.py` (`labor-2021.json` = Хөдөлмөрийн тухай хууль, 2021 revised) | real |
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

1. Find the lawId of the law in force: `cd data && python -m pipeline.sources legalinfo find "Зөрчлийн тухай хууль"`.
   Check the page, then add `{law_id, name, legalinfo_id, title_on_legalinfo, source_url}` to `legalinfo_catalog.json`
   (keep the `law_id` the graph already uses for that law, if any).
2. `python scripts/fetch_laws.py` (or `make laws`): saves the page to `raw/laws/<law_id>.html` (not committed) and
   parses it with `../parse_law.py` into `<law_id>.json`. `--force` downloads every page again.
3. Record verified former / short names in `law_names.json`.
4. `python scripts/build_processed_data.py`, then `python scripts/validate_data.py`.

`parse_law.py` reads three numbering styles: "12 дугаар зүйл" + "12.3." (most laws), "7.1 дүгээр зүйл" + "1.", "2.1."
(codes numbered by chapter: Зөрчлийн тухай хууль, Эрүүгийн хууль → 7.1.1, 7.1.2.1) and "Хоёрдугаар зүйл." + "1."
(Үндсэн хууль). Articles inserted later keep their superscript: 9¹, 19¹.1.

## Adding a real bill

Create `raw/drafts/<lawforum_id>.json` (same shape as `fixtures/sample/drafts/*.json`):
`{lawforum_id, title, source_url, text, cosubmitted: [{title, text}]}`. The text is
parsed for amendment wording ("…гэснийг …гэж өөрчилсүгэй", "…гэсний дараа …гэж
нэмсүгэй", "…гэснийг хассугай", "…хүчингүй болсонд тооцсугай", "…нэрийг …гэж
өөрчилсүгэй"). `python -m pipeline.sources lawforum --search …` fetches bill metadata
(the public LawForum API has no bill text).

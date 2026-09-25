PY ?= python3
VENV := .venv
VPY := $(VENV)/bin/python

.PHONY: install up down logs mock real web test test-backend test-data test-web e2e seed laws data validate-data load

install:            ## local venv for backend + data, and web deps
	$(PY) -m venv $(VENV)
	$(VPY) -m pip install -q -r backend/requirements.txt -r data/requirements.txt
	cd web && npm install && npx playwright install chromium

up:                 ## demo stack (MOCK=1): http://localhost:5173
	docker compose up -d --build

down:
	docker compose stop backend web

logs:
	docker compose logs -f backend web

mock:               ## API on :8000 with the [ЖИШЭЭ] sample dataset (no Neo4j)
	cd backend && MOCK=1 ../$(VPY) -m uvicorn app.main:app --reload --port 8000

real:               ## API on :8000 with the REAL data/processed, in memory (no Neo4j)
	cd backend && MOCK=0 GRAPH_BACKEND=memory ../$(VPY) -m uvicorn app.main:app --reload --port 8000

web:                ## Vite dev server on :5173, proxies /api to :8000
	cd web && npm run dev

test: test-backend test-data test-web validate-data

test-backend:
	cd backend && ../$(VPY) -m pytest -q

test-data:
	cd data && ../$(VPY) -m pytest -q

test-web:
	cd web && npm run typecheck && npm test && npm run build

e2e:                ## Playwright smoke test (starts API + Vite itself)
	cd web && npm run e2e

seed:               ## rebuild the [ЖИШЭЭ] sample dataset + endpoint fixtures
	$(VPY) scripts/seed_demo.py

laws:               ## download + parse every law in data/legalinfo_catalog.json (legalinfo.mn)
	$(VPY) scripts/fetch_laws.py

data:               ## rebuild data/processed from real sources
	$(VPY) scripts/build_processed_data.py

validate-data:      ## schema + integrity of data/processed and the sample dataset
	$(VPY) scripts/validate_data.py

load:               ## load data/processed into the Neo4j API graph (NEO4J_* from .env)
	cd backend && ../$(VPY) -m app.graph.loader ../data/processed --reset

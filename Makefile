PY ?= python3
VENV := .venv
VPY := $(VENV)/bin/python

.PHONY: install up down logs mock web test test-backend test-data test-web load validate-data

install:            ## local venv for backend + data, and web deps
	$(PY) -m venv $(VENV)
	$(VPY) -m pip install -q -r backend/requirements.txt -r data/requirements.txt
	cd web && npm install

up:                 ## neo4j + api + web in docker
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api web

mock:               ## API on :8000 serving contracts/fixtures (no Neo4j needed)
	cd backend && MOCK=1 ../$(VPY) -m uvicorn app.main:app --reload --port 8000

web:                ## Vite dev server on :5173, proxies /api to :8000
	cd web && npm run dev

test: test-backend test-data

test-backend:
	cd backend && ../$(VPY) -m pytest -q

test-data:
	cd data && ../$(VPY) -m pytest -q

test-web:
	cd web && npm run build

validate-data:      ## check data/processed/* against contracts/data-format.md
	cd data && ../$(VPY) -m pipeline.validate processed

load:               ## load data/processed into Neo4j
	cd backend && ../$(VPY) -m app.graph.loader ../data/processed

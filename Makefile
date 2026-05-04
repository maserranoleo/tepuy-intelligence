# Tepuy Gas Intelligence — convenience targets.
#
# Loads the project-root .env automatically so all targets see DATABASE_URL.

ifneq (,$(wildcard .env))
include .env
export
endif

VENV       ?= backend/.venv
PY         ?= $(VENV)/bin/python
PIP        ?= $(VENV)/bin/pip
ALEMBIC    ?= $(VENV)/bin/alembic
UVICORN    ?= $(VENV)/bin/uvicorn

.PHONY: help install migrate seed api ingest-gem typecheck-front build-front clean

help:
	@echo "Common tasks:"
	@echo "  make install        Create venv and install backend + ingest deps"
	@echo "  make migrate        Run Alembic migrations against \$$DATABASE_URL"
	@echo "  make seed           Load the manual_seed pipelines"
	@echo "  make api            Run the FastAPI server (auto-reload)"
	@echo "  make ingest-gem FILE=path/to/ggit.xlsx"
	@echo "  make typecheck-front"
	@echo "  make build-front    Production build"
	@echo "  make clean          Remove venv + node_modules"

install:
	test -d $(VENV) || python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e backend[ingest]
	cd frontend && npm install

migrate:
	cd backend && ../$(ALEMBIC) upgrade head

seed:
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.manual_seed.load

api:
	cd backend && PYTHONPATH=..:. ../$(UVICORN) app.main:app --reload --host 127.0.0.1 --port 8000

ingest-gem:
	@test -n "$(FILE)" || (echo "Usage: make ingest-gem FILE=path/to/ggit.xlsx" && exit 1)
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.gem.load "$(FILE)"

typecheck-front:
	cd frontend && npx tsc --noEmit

build-front:
	cd frontend && npm run build

clean:
	rm -rf $(VENV) frontend/node_modules frontend/dist

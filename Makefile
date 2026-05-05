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
	@echo "  make install              Create venv and install backend + ingest deps"
	@echo "  make migrate              Run Alembic migrations against \$$DATABASE_URL"
	@echo "  make seed                 Load the manual_seed pipelines + gas fields"
	@echo "  make api                  Run the FastAPI server (auto-reload)"
	@echo "  make ingest-gem FILE=path/to/ggit.xlsx"
	@echo "  make ingest-firms [DAYS=7] [SOURCE=VIIRS_SNPP_NRT]"
	@echo "  make ingest-ofac  [URL=<override>] [FILE=path/to/SDN.CSV]"
	@echo "  make typecheck-front"
	@echo "  make build-front          Production build"
	@echo "  make clean                Remove venv + node_modules"

install:
	test -d $(VENV) || python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e backend[ingest]
	cd frontend && npm install

migrate:
	cd backend && ../$(ALEMBIC) upgrade head

seed:
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.manual_seed.load

API_PORT ?= 8001

api:
	cd backend && PYTHONPATH=..:. ../$(UVICORN) app.main:app --reload --host 127.0.0.1 --port $(API_PORT)

ingest-gem:
	@test -n "$(FILE)" || (echo "Usage: make ingest-gem FILE=path/to/ggit.xlsx" && exit 1)
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.gem.load "$(FILE)"

ingest-firms:
	@test -n "$$NASA_FIRMS_MAP_KEY" || (echo "NASA_FIRMS_MAP_KEY is not set in .env" && exit 1)
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.firms.load \
		--days $${DAYS:-7} \
		--source $${SOURCE:-VIIRS_SNPP_NRT}

ingest-ofac:
	PYTHONPATH=backend:. $(PY) -m data_pipeline.sources.ofac.load \
		$(if $(URL),--url $(URL)) \
		$(if $(FILE),--file $(FILE))

typecheck-front:
	cd frontend && npx tsc --noEmit

build-front:
	cd frontend && npm run build

clean:
	rm -rf $(VENV) frontend/node_modules frontend/dist

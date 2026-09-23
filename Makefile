.PHONY: setup stage marts gee features train export check-public all api web test lint docs

# Assumes an activated venv (python3 -m venv venv && source venv/bin/activate).
PY = python -m

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	./venv/bin/pip install -e .
	if [ -f web/package.json ]; then cd web && npm install; else echo "web/ not scaffolded yet, skipping (see web/CLAUDE.md, Week 2 task)"; fi
	./venv/bin/pre-commit install

stage:
	$(PY) agritwin.harmonize.run

marts:
	$(PY) agritwin.survey.run

gee:
	$(PY) agritwin.gee.run

features:
	$(PY) agritwin.features.run

train:
	$(PY) agritwin.models.run

export:
	$(PY) agritwin.export.run

check-public:
	python scripts/check_public.py

all: stage marts gee features train export check-public

api:
	uvicorn api.app.main:app --reload --port 8000

web:
	cd web && npm run dev

test:
	pytest -q
	cd web && npm run test -- --run

lint:
	ruff check .
	mypy src api
	cd web && npm run lint && npm run typecheck

docs:
	mkdocs serve

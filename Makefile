PYTHON ?= backend/venv/bin/python
UV = backend/venv/bin/uv

.PHONY: setup check lint typecheck format-check docs dependencies duplicates test test-backend test-frontend test-stability e2e build build-frontend qa schema lock analyze profile-backend profile-frontend monitoring-check

setup:
	python3 -m venv backend/venv
	$(PYTHON) -m pip install --require-hashes -r requirements-dev.txt
	npm --prefix frontend ci
	$(PYTHON) -m pre_commit install

check: lint typecheck format-check docs dependencies duplicates

lint:
	$(PYTHON) -m ruff check backend scripts
	npm --prefix frontend run lint

typecheck:
	$(PYTHON) -m mypy
	npm --prefix frontend run type-check

format-check:
	$(PYTHON) -m ruff format --check backend scripts
	npm --prefix frontend run format:check

docs:
	$(PYTHON) scripts/check_repo.py
	$(PYTHON) scripts/export_openapi.py --check

dependencies:
	$(PYTHON) -m deptry backend/app
	$(PYTHON) scripts/check_dependency_weight.py
	npm --prefix frontend run check:unused

duplicates:
	npm --prefix frontend run check:duplicates

test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest -n 2 --cov --cov-report=xml:reports/backend-coverage.xml --junitxml=reports/python-tests.xml

test-frontend:
	npm --prefix frontend run test:coverage

test-stability:
	$(PYTHON) -m pytest -n 2 --count=3 --junitxml=reports/backend-stability.xml

e2e:
	npm --prefix frontend run test:e2e

build: build-frontend

build-frontend:
	$(PYTHON) scripts/time_build.py -- npm --prefix frontend run build

qa:
	python3 scripts/run_qa.py

schema:
	$(PYTHON) scripts/export_openapi.py

lock:
	$(UV) pip compile backend/requirements-ml.in --python-version 3.12 --universal --generate-hashes --quiet -o backend/requirements.txt
	$(UV) pip compile backend/requirements-minimal.in -c backend/requirements.txt --python-version 3.12 --universal --generate-hashes --quiet -o backend/requirements_minimal.txt
	$(UV) pip compile requirements-dev.in -c backend/requirements.txt -c backend/requirements_minimal.txt --python-version 3.12 --universal --generate-hashes --quiet -o requirements-dev.txt
	$(UV) pip compile backend/requirements-deploy.in -c requirements-dev.txt --python-version 3.12 --universal --generate-hashes --quiet -o backend/requirements-deploy.txt

analyze:
	npm --prefix frontend run analyze

profile-backend:
	mkdir -p reports
	cd backend && venv/bin/python -m cProfile -o ../reports/backend.prof -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log

profile-frontend:
	mkdir -p reports
	cd frontend && node --cpu-prof --cpu-prof-dir=../reports node_modules/next/dist/bin/next dev --hostname 127.0.0.1

monitoring-check:
	docker run --rm --entrypoint promtool -v "$(CURDIR)/monitoring:/etc/prometheus:ro" prom/prometheus:v3.9.1 check config /etc/prometheus/prometheus.yml
	docker run --rm --entrypoint promtool -w /etc/prometheus -v "$(CURDIR)/monitoring:/etc/prometheus:ro" prom/prometheus:v3.9.1 test rules alerts.test.yml

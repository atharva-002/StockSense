.PHONY: help install train evaluate drift test serve docker-build docker-up fmt lint

PY ?= python3

help:
	@echo "Available targets:"
	@echo "  install        pip install training deps"
	@echo "  train          train models + produce backend/artifacts"
	@echo "  evaluate       run quality gate on current metrics.json"
	@echo "  drift          compute drift report from data/new/"
	@echo "  test           pytest tests/"
	@echo "  serve          run FastAPI locally on :8001"
	@echo "  docker-build   build the API docker image"
	@echo "  docker-up      run api + mlflow via compose"
	@echo "  lint           ruff lint"
	@echo "  fmt            ruff format"

install:
	$(PY) -m pip install -r backend/requirements-train.txt

train:
	MLFLOW_ALLOW_FILE_STORE=true $(PY) -m ml.train --data data/raw/train.csv --out backend/artifacts --mlruns mlruns

evaluate:
	$(PY) -m ml.evaluate --metrics backend/artifacts/metrics.json

drift:
	$(PY) -m ml.drift --train data/raw/train.csv --new data/new/new_sales.csv --out backend/artifacts/drift_report.json

test:
	$(PY) -m pytest tests/ -q

serve:
	cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload

docker-build:
	docker build -t stocksense-api:latest -f Dockerfile .

docker-up:
	docker compose up --build api mlflow

lint:
	ruff check .

fmt:
	ruff format .

.PHONY: help install test run docker-build docker-run clean

help:
	@echo "NGAQuant Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install dependencies"
	@echo "  test         - Run tests"
	@echo "  run          - Run CLI"
	@echo "  web          - Run Web UI"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run with Docker Compose"
	@echo "  clean        - Clean generated files"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	python cli.py analyze --tid $(tid)

web:
	streamlit run web/app.py

docker-build:
	docker build -t ngaquant:latest .

docker-run:
	docker-compose up -d

clean:
	rm -rf __pycache__ .pytest_cache logs/*.log output/*.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

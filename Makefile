.PHONY: install lint test check clean

install: ## Install the project with dev dependencies
	uv sync --group dev

lint: ## Run ruff linter and formatter check
	uv run ruff check src tests
	uv run ruff format --check src tests

format: ## Auto-format code
	uv run ruff check --fix src tests
	uv run ruff format src tests

test: ## Run tests
	uv run pytest -v

check: lint test ## Run all checks (lint + test)

clean: ## Remove build artifacts
	rm -rf dist build *.egg-info .pytest_cache htmlcov .coverage __pycache__

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

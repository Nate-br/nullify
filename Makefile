.PHONY: install dev test lint format clean

install:       ## Create .venv and install runtime dependencies
	uv sync

dev:           ## Install runtime + dev/static extras
	uv sync --extra dev --extra static

test:          ## Run the test suite
	uv run pytest

lint:          ## Ruff lint
	uv run ruff check src tests

format:        ## Ruff format
	uv run ruff format src tests

clean:         ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .venv dist build src/nullify.egg-info

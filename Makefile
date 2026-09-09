.PHONY: install dev test lint format clean run-web run-tui build

install:       ## Create .venv and install runtime dependencies
	uv sync

dev:           ## Install runtime + all extras for dev and testing
	uv sync --all-extras

test:          ## Run the test suite
	uv run pytest

lint:          ## Ruff lint
	uv run ruff check src tests scripts

format:        ## Ruff format
	uv run ruff format src tests scripts

run-web:       ## Run the Web UI
	uv run nullify web

run-tui:       ## Run the TUI
	uv run nullify tui

build:         ## Build wheel and sdist
	uv build

clean:         ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .venv dist build src/nullify.egg-info

.PHONY: install test lint clean

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check .

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info dist build .ruff_cache
	find . -name __pycache__ -exec rm -rf {} +

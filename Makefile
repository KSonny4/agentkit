.PHONY: install test lint clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info dist build .ruff_cache
	find . -name __pycache__ -exec rm -rf {} +

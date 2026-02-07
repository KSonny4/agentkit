.PHONY: install test lint clean run check-auth

PROFILE ?= playground

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check .

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info dist build .ruff_cache
	find . -name __pycache__ -exec rm -rf {} +

check-auth:
	@claude -p "ok" > /dev/null 2>&1 && echo "✓ Claude auth OK" || \
		(echo "✗ Auth failed — run 'claude' to re-login" && exit 1)

run: check-auth
	@test -f .env && export $$(grep -v '^\#' .env | xargs) ; \
	uv run agentkit run --profile $(PROFILE)

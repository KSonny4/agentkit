.PHONY: install test lint clean run task evaluate check-auth

PROFILE ?= playground
PROMPT  ?= hello
WRITE   ?=

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
	@claude -p "say ok" > /dev/null 2>&1 && echo "✓ Claude auth works" || \
		(echo "✗ Claude auth failed — run 'claude' to re-login" && exit 1)

run: check-auth
	@test -f .env && export $$(grep -v '^\#' .env | xargs) ; \
	echo "=== agentkit daemon ===" ; \
	echo "Profile: $(PROFILE)" ; \
	echo "Starting..." ; \
	uv run agentkit run --profile $(PROFILE)

task: check-auth
	@uv run agentkit task --profile $(PROFILE) $(if $(WRITE),--write,) "$(PROMPT)"

evaluate: check-auth
	@uv run agentkit evaluate --profile $(PROFILE)

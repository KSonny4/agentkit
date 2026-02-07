.PHONY: install test lint clean run agent stop check-auth

PROFILE ?= playground
PID_FILE = .agent.pid

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

stop:
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null && echo "✓ Stopped agent (pid $$(cat $(PID_FILE)))" || echo "Agent not running"; \
		rm -f $(PID_FILE); \
	else \
		echo "No agent running"; \
	fi

run: check-auth
	@export $$(grep -v '^\#' .env | xargs) ; \
	uv run agentkit run --profile $(PROFILE)

agent: stop check-auth
	@echo "=== Starting agent (profile: $(PROFILE)) ==="
	@rm -f profiles/$(PROFILE)/heartbeat.md
	@rm -f data/agentkit.db
	@export $$(grep -v '^\#' .env | xargs) ; \
	nohup uv run agentkit run --profile $(PROFILE) > logs/agent.log 2>&1 & \
	echo $$! > $(PID_FILE) && \
	echo "✓ Agent running (pid $$!, log: logs/agent.log)"

logs:
	@tail -f logs/agent.log

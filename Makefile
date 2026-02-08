.PHONY: install test lint clean run agent update-agent stop check-auth reset spy status spy-report

PROFILE ?= playground
PID_FILE = .agent.pid
LOG ?= 20

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
	@for plist in ~/Library/LaunchAgents/com.agentkit.*.plist; do \
		[ -f "$$plist" ] && launchctl unload "$$plist" 2>/dev/null && rm -f "$$plist" && echo "✓ Removed $$(basename $$plist)"; \
	done; true

run: check-auth
	@export $$(grep -v '^\#' .env | xargs) ; \
	uv run agentkit run --profile $(PROFILE)

agent: stop check-auth
	@echo "=== Starting agent (profile: $(PROFILE)) ==="
	@rm -f data/agentkit.db
	@crontab -r 2>/dev/null || true
	@export $$(grep -v '^\#' .env | xargs) ; \
	nohup uv run agentkit run --profile $(PROFILE) > logs/agent.log 2>&1 & \
	echo $$! > $(PID_FILE) && \
	echo "✓ Agent running (pid $$!, log: logs/agent.log)"

update-agent: stop check-auth
	@echo "=== Restarting agent (profile: $(PROFILE), keeping state) ==="
	@export $$(grep -v '^\#' .env | xargs) ; \
	nohup uv run agentkit run --profile $(PROFILE) > logs/agent.log 2>&1 & \
	echo $$! > $(PID_FILE) && \
	echo "✓ Agent running (pid $$!, log: logs/agent.log)"

reset: stop
	@echo "=== Wiping memory + DB ==="
	@rm -f data/agentkit.db
	@rm -f memory/daily/*.md
	@echo "# Long-Term Memory\n\nThis file stores persistent observations and learned facts." > memory/MEMORY.md
	@echo "✓ Clean slate"

logs:
	@tail -f logs/agent.log

status:
	@AGENT_PROFILE=$(PROFILE) scripts/spy.sh $(LOG)

spy:
	@echo "Watching agent (Ctrl-C to stop)..."
	@while true; do \
		AGENT_PROFILE=$(PROFILE) scripts/spy.sh $(LOG); \
		sleep 5; \
	done

spy-report:
	@scripts/spy-report.sh

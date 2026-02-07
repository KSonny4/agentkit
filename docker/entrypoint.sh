#!/usr/bin/env bash
set -euo pipefail

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ERROR: ANTHROPIC_API_KEY is required"
    exit 1
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN is required"
    exit 1
fi

echo "=== agentkit daemon ==="
echo "Profile: ${AGENT_PROFILE:-playground}"
echo "Starting..."

exec uv run python -m agentkit "$@"

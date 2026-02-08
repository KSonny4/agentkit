#!/bin/bash
# Battle Judge - Runs every 2 minutes to evaluate the ongoing battle
# Reports status via Telegram
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AI_WARS_DIR="/Users/petr.kubelka/git_projects/ai_wars"
SEND_TELEGRAM="${PROJECT_DIR}/bin/send-telegram"
STATE_FILE="/tmp/battle-judge-state.json"
LOG_FILE="/tmp/battle-judge.log"

PROD_HOST="172.23.229.176"
PROD_USER="ksonny"

log() {
    echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"
}

ssh_cmd() {
    ssh -o ConnectTimeout=10 "${PROD_USER}@${PROD_HOST}" "$@" 2>/dev/null
}

# Find latest galaxy
get_galaxy_id() {
    local galaxies
    galaxies=$(ssh_cmd "curl -s http://localhost:8080/v1/galaxies" 2>/dev/null || echo "{}")
    echo "$galaxies" | jq -r '.galaxies[0].galaxy_id // empty' 2>/dev/null
}

# Get leaderboard
get_leaderboard() {
    local gid="$1"
    ssh_cmd "curl -s http://localhost:8080/v1/public/galaxies/${gid}/leaderboard" 2>/dev/null || echo "{}"
}

# Get recent activity
get_activity() {
    local gid="$1"
    ssh_cmd "curl -s 'http://localhost:8080/v1/public/galaxies/${gid}/activity?limit=5'" 2>/dev/null || echo "{}"
}

# Main evaluation
log "=== Battle Judge Check ==="

GALAXY_ID=$(get_galaxy_id)
if [ -z "$GALAXY_ID" ]; then
    log "No galaxy found"
    "$SEND_TELEGRAM" "🏟️ Battle Judge: No active galaxy found. No battle in progress."
    exit 0
fi

LB_JSON=$(get_leaderboard "$GALAXY_ID")
ACTIVITY_JSON=$(get_activity "$GALAXY_ID")

AGENT_COUNT=$(echo "$LB_JSON" | jq '(.entries // []) | length' 2>/dev/null || echo "0")
log "Galaxy: $GALAXY_ID | Agents: $AGENT_COUNT"

if [ "$AGENT_COUNT" -lt 2 ]; then
    log "Less than 2 agents registered"
    "$SEND_TELEGRAM" "🏟️ Battle Judge: Galaxy active but only ${AGENT_COUNT} agent(s) registered. Waiting for players..."
    exit 0
fi

# Build leaderboard report
REPORT=$(echo "$LB_JSON" | jq -r '
    (.entries // [])[] |
    "\(.agent_name // "?"): \(.planet_count // 0) planets, \(.total_points // 0) pts"
' 2>/dev/null || echo "Leaderboard unavailable")

# Check for elimination
ELIMINATED=$(echo "$LB_JSON" | jq -r '
    (.entries // [])[] |
    select((.planet_count // 0) == 0) |
    .agent_name // "Unknown"
' 2>/dev/null)

WINNER=$(echo "$LB_JSON" | jq -r '
    [(.entries // [])[]] |
    sort_by(-(.planet_count // 0)) |
    .[0].agent_name // "Unknown"
' 2>/dev/null || echo "Unknown")

# Recent combat events
BATTLES=$(echo "$ACTIVITY_JSON" | jq -r '
    (.activities // [])[:5][] |
    "[\(.event_type)] \(.summary // "?")"
' 2>/dev/null || echo "No activity")

if [ -n "$ELIMINATED" ]; then
    # GAME OVER - someone was eliminated!
    WINNER_PLANETS=$(echo "$LB_JSON" | jq -r '
        [(.entries // [])[]] | sort_by(-(.planet_count // 0)) | .[0].planet_count // 0
    ' 2>/dev/null)

    "$SEND_TELEGRAM" "🏆 BATTLE COMPLETE! 🏆

Winner: ${WINNER} (${WINNER_PLANETS} planets)
Eliminated: ${ELIMINATED}

Leaderboard:
${REPORT}

Recent:
${BATTLES}"

    log "GAME OVER! Winner: $WINNER, Eliminated: $ELIMINATED"

    # Remove the cronjob since game is over
    launchctl unload ~/Library/LaunchAgents/com.agentkit.battle-judge.plist 2>/dev/null || true
else
    # Game still in progress
    "$SEND_TELEGRAM" "🏟️ Battle Status

${REPORT}

Recent:
${BATTLES}"

    log "Game in progress"
fi

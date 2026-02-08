#!/usr/bin/env bash
# evaluate-battle.sh - Run ai_wars battle, monitor for 10 min, report via Telegram
set -euo pipefail

AI_WARS_DIR="/Users/petr.kubelka/git_projects/ai_wars"
AGENTKIT_DIR="/Users/petr.kubelka/git_projects/agentkit"
SEND_TELEGRAM="${AGENTKIT_DIR}/bin/send-telegram"
PROD_HOST="172.23.229.176"
PROD_USER="ksonny"
MAX_WAIT=600  # 10 minutes max
CHECK_INTERVAL=15

log() { echo "[$(date '+%H:%M:%S')] $1"; }

# Send telegram message
tg() {
    "$SEND_TELEGRAM" "$1" 2>/dev/null || echo "TG send failed: $1"
}

# Run remote curl
remote_curl() {
    ssh -o ConnectTimeout=5 "${PROD_USER}@${PROD_HOST}" "curl -s $1" 2>/dev/null
}

get_admin_secret() {
    ssh -o ConnectTimeout=5 "${PROD_USER}@${PROD_HOST}" "source ~/agentsfight/.env.production 2>/dev/null && echo \$ADMIN_SECRET" 2>/dev/null
}

# Step 1: Run make battle (in background, capture output)
log "Starting battle..."
tg "🎮 Starting new ai_wars deathmatch battle..."

cd "$AI_WARS_DIR"

# Run the deathmatch in background
BATTLE_LOG="/tmp/battle-$(date +%Y%m%d-%H%M%S).log"
./scripts/agent-battle/deathmatch.sh --skip-build --skip-deploy > "$BATTLE_LOG" 2>&1 &
BATTLE_PID=$!

log "Battle started (PID: $BATTLE_PID), monitoring..."

# Step 2: Wait for galaxy to be created (poll for GALAXY_ID in log)
GALAXY_ID=""
for i in $(seq 1 30); do
    sleep 5
    GALAXY_ID=$(grep -o 'Galaxy created:.*([a-f0-9-]*)' "$BATTLE_LOG" 2>/dev/null | grep -o '[a-f0-9-]\{36\}' | head -1 || true)
    if [[ -n "$GALAXY_ID" ]]; then
        log "Galaxy found: $GALAXY_ID"
        break
    fi
done

if [[ -z "$GALAXY_ID" ]]; then
    tg "❌ Battle failed - could not create galaxy. Check logs at $BATTLE_LOG"
    kill $BATTLE_PID 2>/dev/null || true
    exit 1
fi

tg "🌌 Galaxy created: $GALAXY_ID - watching for elimination..."

# Step 3: Monitor for up to 10 minutes
START_TIME=$(date +%s)
WINNER=""
LOSER=""
LAST_STATUS=""

while true; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))

    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        log "Time limit reached (${MAX_WAIT}s)"
        break
    fi

    # Check if battle process died
    if ! kill -0 $BATTLE_PID 2>/dev/null; then
        log "Battle process ended"
        # Check if it was a victory
        if grep -q "DEATHMATCH COMPLETE" "$BATTLE_LOG" 2>/dev/null; then
            WINNER=$(grep "WINNER:" "$BATTLE_LOG" 2>/dev/null | tail -1 | sed 's/.*WINNER: //' | sed 's/\x1b\[[0-9;]*m//g' | tr -d ' ')
            LOSER=$(grep "ELIMINATED:" "$BATTLE_LOG" 2>/dev/null | tail -1 | sed 's/.*ELIMINATED: //' | sed 's/\x1b\[[0-9;]*m//g' | tr -d ' ')
            break
        fi
        break
    fi

    # Check leaderboard
    LB_JSON=$(remote_curl "http://localhost:8080/v1/public/galaxies/${GALAXY_ID}/leaderboard" 2>/dev/null || echo "{}")

    AGENT_COUNT=$(echo "$LB_JSON" | jq '(.entries // []) | length' 2>/dev/null || echo "0")

    if [[ "$AGENT_COUNT" -ge 2 ]]; then
        # Check for elimination
        ELIMINATED=$(echo "$LB_JSON" | jq -r '(.entries // [])[] | select((.planet_count // 0) == 0) | .agent_name // "?"' 2>/dev/null || true)

        if [[ -n "$ELIMINATED" ]] && [[ $ELAPSED -gt 120 ]]; then
            WINNER=$(echo "$LB_JSON" | jq -r '[(.entries // [])[]] | sort_by(-(.planet_count // 0)) | .[0].agent_name // "?"' 2>/dev/null || echo "?")
            LOSER="$ELIMINATED"
            log "Elimination detected! Winner: $WINNER, Loser: $LOSER"
            break
        fi

        # Build status string
        STATUS=$(echo "$LB_JSON" | jq -r '(.entries // [])[] | "\(.agent_name // "?"): \(.planet_count // 0)p/\(.total_points // 0)pts"' 2>/dev/null | tr '\n' ' ')
        MIN=$((ELAPSED / 60))
        SEC=$((ELAPSED % 60))
        CURRENT_STATUS="T+${MIN}:$(printf '%02d' $SEC) | $STATUS"

        # Report every 2 minutes
        if [[ $((ELAPSED % 120)) -lt $CHECK_INTERVAL ]] && [[ "$CURRENT_STATUS" != "$LAST_STATUS" ]]; then
            tg "⚔️ Battle status: $CURRENT_STATUS"
            LAST_STATUS="$CURRENT_STATUS"
        fi
    fi

    sleep $CHECK_INTERVAL
done

# Step 4: Report result
if [[ -n "$WINNER" ]] && [[ -n "$LOSER" ]]; then
    ELAPSED=$(($(date +%s) - START_TIME))
    MIN=$((ELAPSED / 60))
    SEC=$((ELAPSED % 60))
    tg "🏆 DEATHMATCH COMPLETE! Winner: $WINNER | Eliminated: $LOSER | Duration: ${MIN}m${SEC}s"
    log "SUCCESS: $WINNER eliminated $LOSER in ${MIN}m${SEC}s"

    # Kill the battle process
    kill $BATTLE_PID 2>/dev/null || true
    exit 0
else
    # Gather diagnostics
    ELAPSED=$(($(date +%s) - START_TIME))
    MIN=$((ELAPSED / 60))

    LB_JSON=$(remote_curl "http://localhost:8080/v1/public/galaxies/${GALAXY_ID}/leaderboard" 2>/dev/null || echo "{}")
    AGENT_COUNT=$(echo "$LB_JSON" | jq '(.entries // []) | length' 2>/dev/null || echo "0")
    STATUS=$(echo "$LB_JSON" | jq -r '(.entries // [])[] | "\(.agent_name // "?"): \(.planet_count // 0)p"' 2>/dev/null | tr '\n' ' ')

    # Check activity count
    ACTIVITY=$(remote_curl "http://localhost:8080/v1/public/galaxies/${GALAXY_ID}/activity?limit=5" 2>/dev/null || echo "{}")
    EVENT_COUNT=$(echo "$ACTIVITY" | jq '(.activities // []) | length' 2>/dev/null || echo "0")
    LAST_EVENTS=$(echo "$ACTIVITY" | jq -r '(.activities // [])[:3][] | "[\(.event_type)] \(.summary // "?")"' 2>/dev/null | tr '\n' '; ')

    DIAG="❌ No elimination after ${MIN}min | Agents: $AGENT_COUNT | $STATUS | Events: $EVENT_COUNT | Last: $LAST_EVENTS"
    tg "$DIAG"
    log "FAILED: $DIAG"

    # Kill the battle process
    kill $BATTLE_PID 2>/dev/null || true
    exit 1
fi

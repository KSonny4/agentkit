#!/usr/bin/env bash
# spy.sh — detailed real-time view of what's happening inside your agentkit agent
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$PROJECT_ROOT/data/agentkit.db"
PID_FILE="$PROJECT_ROOT/.agent.pid"
LOG_FILE="$PROJECT_ROOT/logs/agent.log"
MEMORY_DIR="$PROJECT_ROOT/memory"
PROFILE="${AGENT_PROFILE:-playground}"
PROFILE_DIR="$PROJECT_ROOT/profiles/$PROFILE"

# Colors
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
RESET='\033[0m'

LOG_LINES="${1:-5}"
NOW_EPOCH=$(date +%s)

# Convert ISO timestamp (UTC) or "ps lstart" to "Xm ago" / "Xh Ym ago" etc.
time_ago() {
    local ts="$1"
    local then_epoch

    # Try ISO format first (2026-02-07T23:12:07...), then ps lstart format
    if [[ "$ts" == *T* ]]; then
        # ISO — strip timezone suffix, parse with date
        local clean="${ts%%+*}"  # drop +00:00
        clean="${clean%%Z}"      # drop Z
        then_epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%S" "$clean" +%s 2>/dev/null || echo 0)
    else
        # ps lstart format (e.g. "Sat Feb  7 23:27:35 2026")
        then_epoch=$(date -j -f "%a %b %d %H:%M:%S %Y" "$ts" +%s 2>/dev/null || echo 0)
    fi

    if [ "$then_epoch" -eq 0 ]; then
        echo "$ts"
        return
    fi

    local diff=$((NOW_EPOCH - then_epoch))
    if [ "$diff" -lt 0 ]; then diff=0; fi

    if [ "$diff" -lt 60 ]; then
        echo "${diff}s ago"
    elif [ "$diff" -lt 3600 ]; then
        echo "$((diff / 60))m $((diff % 60))s ago"
    elif [ "$diff" -lt 86400 ]; then
        echo "$((diff / 3600))h $((diff % 3600 / 60))m ago"
    else
        echo "$((diff / 86400))d $((diff % 86400 / 3600))h ago"
    fi
}

divider() {
    printf "${DIM}%.0s─${RESET}" {1..70}
    echo
}

section() {
    echo
    printf "${BOLD}${CYAN}▸ %s${RESET}\n" "$1"
    divider
}

# ── Header ──────────────────────────────────────────────────────────
clear 2>/dev/null || true
echo
printf "${BOLD}${MAGENTA}  ╔═══════════════════════════════════════════╗${RESET}\n"
printf "${BOLD}${MAGENTA}  ║        agentkit spy — agent monitor       ║${RESET}\n"
printf "${BOLD}${MAGENTA}  ╚═══════════════════════════════════════════╝${RESET}\n"
printf "${DIM}  %s${RESET}\n" "$(date '+%Y-%m-%d %H:%M:%S')"

# ── 1. Process Status ───────────────────────────────────────────────
section "PROCESS STATUS"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        # Get process start time and compute uptime
        START_TIME=$(ps -o lstart= -p "$PID" 2>/dev/null | xargs)
        CPU=$(ps -o %cpu= -p "$PID" 2>/dev/null | xargs)
        MEM=$(ps -o rss= -p "$PID" 2>/dev/null | xargs)
        MEM_MB=$((MEM / 1024))
        UPTIME=$(time_ago "$START_TIME")
        printf "  ${GREEN}● RUNNING${RESET}  PID: ${BOLD}%s${RESET}  Uptime: ${BOLD}%s${RESET}\n" "$PID" "$UPTIME"
        printf "  Started:  %s\n" "$START_TIME"
        printf "  CPU: %s%%   Memory: %s MB\n" "$CPU" "$MEM_MB"

        # Count child processes (Claude CLI calls)
        CHILDREN=$(pgrep -P "$PID" 2>/dev/null | wc -l | xargs)
        if [ "$CHILDREN" -gt 0 ]; then
            printf "  ${YELLOW}⚡ Active child processes: %s (agent is thinking)${RESET}\n" "$CHILDREN"
            # Show what the children are doing
            pgrep -P "$PID" 2>/dev/null | while read CPID; do
                CMD=$(ps -o command= -p "$CPID" 2>/dev/null | head -c 80)
                printf "    └─ PID %s: %s\n" "$CPID" "$CMD"
            done
        else
            printf "  ${DIM}  No active child processes (agent idle, waiting for input)${RESET}\n"
        fi
    else
        printf "  ${RED}● DEAD${RESET}  PID file exists (%s) but process not running\n" "$PID"
        printf "  ${DIM}  Run 'make agent' to restart${RESET}\n"
    fi
else
    printf "  ${RED}● STOPPED${RESET}  No PID file found\n"
    printf "  ${DIM}  Run 'make agent' to start, or 'make run' for foreground${RESET}\n"
fi

# ── 2. Profile ──────────────────────────────────────────────────────
section "PROFILE: $PROFILE"

if [ -f "$PROFILE_DIR/identity.md" ]; then
    printf "  ${BOLD}Identity:${RESET}\n"
    sed 's/^/    /' "$PROFILE_DIR/identity.md" | head -5
    IDENTITY_LINES=$(wc -l < "$PROFILE_DIR/identity.md" | xargs)
    [ "$IDENTITY_LINES" -gt 5 ] && printf "    ${DIM}... (%s total lines)${RESET}\n" "$IDENTITY_LINES"
else
    printf "  ${YELLOW}No identity.md found${RESET}\n"
fi

if [ -f "$PROFILE_DIR/tools.md" ]; then
    TOOL_COUNT=$(grep -c '^\- \|^### ' "$PROFILE_DIR/tools.md" 2>/dev/null || echo 0)
    printf "  ${BOLD}Tools:${RESET} %s directives/skills defined\n" "$TOOL_COUNT"
fi

# ── 3. Mailbox (Task Queue) ────────────────────────────────────────
section "MAILBOX (TASK QUEUE)"

if [ -f "$DB" ]; then
    # Status counts
    PENDING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE status='pending';" 2>/dev/null || echo 0)
    PROCESSING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE status='processing';" 2>/dev/null || echo 0)
    DONE=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE status='done';" 2>/dev/null || echo 0)
    FAILED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE status='failed';" 2>/dev/null || echo 0)
    TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks;" 2>/dev/null || echo 0)

    printf "  ${YELLOW}⏳ Pending: %s${RESET}   " "$PENDING"
    printf "${BLUE}⚙  Processing: %s${RESET}   " "$PROCESSING"
    printf "${GREEN}✓ Done: %s${RESET}   " "$DONE"
    printf "${RED}✗ Failed: %s${RESET}   " "$FAILED"
    printf "${DIM}Total: %s${RESET}\n" "$TOTAL"

    # Currently processing task
    if [ "$PROCESSING" -gt 0 ]; then
        echo
        printf "  ${BOLD}${BLUE}Currently processing:${RESET}\n"
        sqlite3 "$DB" "
            SELECT id, replace(substr(content, 1, 60), char(10), ' '), source, substr(updated_at, 1, 19)
            FROM tasks WHERE status='processing';
        " 2>/dev/null | while IFS='|' read -r ID TASK SRC UPDATED; do
            ELAPSED=$(time_ago "$UPDATED")
            printf "    ${BLUE}⚙${RESET}  #%-3s ${BOLD}%s${RESET}\n" "$ID" "$TASK"
            printf "         ${DIM}from %s — started %s${RESET}\n" "$SRC" "$ELAPSED"
        done
    fi

    # Pending tasks
    if [ "$PENDING" -gt 0 ]; then
        echo
        printf "  ${BOLD}${YELLOW}Waiting in queue:${RESET}\n"
        sqlite3 "$DB" "
            SELECT id, replace(substr(content, 1, 60), char(10), ' '), source, substr(created_at, 1, 19)
            FROM tasks WHERE status='pending' ORDER BY id;
        " 2>/dev/null | while IFS='|' read -r ID TASK SRC CREATED; do
            AGO=$(time_ago "$CREATED")
            printf "    ${YELLOW}⏳${RESET} #%-3s %s  ${DIM}[%s, queued %s]${RESET}\n" "$ID" "$TASK" "$SRC" "$AGO"
        done
    fi

    # Recent task history
    echo
    printf "  ${BOLD}Recent history (last 10):${RESET}\n"
    sqlite3 "$DB" "
        SELECT
            id,
            status,
            replace(substr(content, 1, 45), char(10), ' '),
            source,
            substr(updated_at, 1, 19)
        FROM tasks ORDER BY id DESC LIMIT 10;
    " 2>/dev/null | while IFS='|' read -r ID ST TASK SRC UPDATED; do
        case "$ST" in
            done)       SYM="✓"; COLOR="$GREEN" ;;
            failed)     SYM="✗"; COLOR="$RED" ;;
            processing) SYM="⚙"; COLOR="$BLUE" ;;
            *)          SYM="⏳"; COLOR="$YELLOW" ;;
        esac
        AGO=$(time_ago "$UPDATED")
        printf "    ${COLOR}%s${RESET} #%-3s ${BOLD}%s${RESET}  ${DIM}[%s, %s]${RESET}\n" "$SYM" "$ID" "$TASK" "$SRC" "$AGO"
    done

    # Failed tasks detail
    if [ "$FAILED" -gt 0 ]; then
        echo
        printf "  ${BOLD}${RED}Failed tasks:${RESET}\n"
        sqlite3 "$DB" "
            SELECT id, replace(substr(content, 1, 40), char(10), ' '), substr(result, 1, 60), updated_at
            FROM tasks WHERE status='failed' ORDER BY id DESC LIMIT 5;
        " 2>/dev/null | while IFS='|' read -r ID TASK ERR UPDATED; do
            printf "    ${RED}#%-3s${RESET} %s\n" "$ID" "$TASK"
            printf "         ${DIM}Error: %s${RESET}\n" "$ERR"
        done
    fi
else
    printf "  ${DIM}No database found at %s${RESET}\n" "$DB"
    printf "  ${DIM}Agent hasn't been started yet or DB was reset${RESET}\n"
fi

# ── 4. Live Progress ──────────────────────────────────────────────
PROGRESS="$PROJECT_ROOT/data/progress.jsonl"
if [ -f "$PROGRESS" ] && [ -s "$PROGRESS" ]; then
    # Show if file was modified recently (within last 30 min)
    PROG_MOD=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$PROGRESS" 2>/dev/null || echo "")
    PROG_AGO=""
    PROG_STALE=false
    if [ -n "$PROG_MOD" ]; then
        PROG_MOD_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$PROG_MOD" +%s 2>/dev/null || echo 0)
        PROG_DIFF=$((NOW_EPOCH - PROG_MOD_EPOCH))
        [ "$PROG_DIFF" -gt 1800 ] && PROG_STALE=true
        PROG_AGO=$(time_ago "$PROG_MOD")
    fi

    if [ "$PROG_STALE" = false ]; then
        section "LIVE PROGRESS"
        printf "  ${DIM}%s — updated %s${RESET}\n\n" "$PROGRESS" "$PROG_AGO"

        # Parse stream-json events with python3
        python3 -c "
import json, sys

tool_calls = []
texts = []
result = None
errors = []
total = 0

for line in open('$PROGRESS'):
    line = line.strip()
    if not line:
        continue
    total += 1
    try:
        e = json.loads(line)
        t = e.get('type', '')
        if t == 'result':
            result = e.get('result', '')
            sub = e.get('subtype', '')
            if sub == 'error':
                errors.append(e.get('error', 'unknown error'))
        elif t == 'assistant':
            msg = e.get('message', {})
            for block in msg.get('content', []):
                bt = block.get('type', '')
                if bt == 'tool_use':
                    name = block.get('name', '?')
                    inp = block.get('input', {})
                    # Summarize input
                    if 'command' in inp:
                        detail = inp['command'][:60]
                    elif 'file_path' in inp:
                        detail = inp['file_path']
                    elif 'pattern' in inp:
                        detail = inp['pattern']
                    elif 'query' in inp:
                        detail = inp['query'][:60]
                    elif 'url' in inp:
                        detail = inp['url'][:60]
                    else:
                        detail = json.dumps(inp)[:50]
                    tool_calls.append(f'{name}: {detail}')
                elif bt == 'text':
                    txt = block.get('text', '').strip()
                    if txt:
                        texts.append(txt)
    except (json.JSONDecodeError, KeyError):
        pass

# Output summary
print(f'  Events: {total}   Tool calls: {len(tool_calls)}')
print()

if result is not None:
    print('  \033[0;32mTask completed\033[0m')
    snippet = result[:150].replace(chr(10), ' ')
    if snippet:
        print(f'  Result: {snippet}')
elif errors:
    for err in errors:
        print(f'  \033[0;31mError: {err[:100]}\033[0m')
else:
    print('  \033[0;34mTask in progress...\033[0m')

if tool_calls:
    print()
    print('  \033[1mRecent tool calls:\033[0m')
    for tc in tool_calls[-8:]:
        print(f'    \033[0;36m>\033[0m {tc[:75]}')

if texts:
    last = texts[-1][:120].replace(chr(10), ' ')
    print()
    print(f'  \033[2mLast output: {last}\033[0m')
" 2>/dev/null
    fi
fi

# ── 5. Memory State ────────────────────────────────────────────────
section "MEMORY"

# Long-term memory
LTM="$MEMORY_DIR/MEMORY.md"
if [ -f "$LTM" ]; then
    LTM_LINES=$(wc -l < "$LTM" | xargs)
    LTM_SIZE=$(wc -c < "$LTM" | xargs)
    LTM_MOD=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$LTM" 2>/dev/null || echo "")
    LTM_AGO=""
    [ -n "$LTM_MOD" ] && LTM_AGO=" (modified $(time_ago "$LTM_MOD"))"
    printf "  ${BOLD}Long-term memory:${RESET} %s lines, %s bytes${DIM}%s${RESET}\n" "$LTM_LINES" "$LTM_SIZE" "$LTM_AGO"
    printf "  ${DIM}%s${RESET}\n" "$LTM"
    echo
    # Show last 8 non-empty lines
    grep -v '^$' "$LTM" | tail -8 | while read -r LINE; do
        printf "    %s\n" "$LINE"
    done
    echo
else
    printf "  ${DIM}No long-term memory file${RESET}\n"
fi

# Daily memories
printf "  ${BOLD}Daily observations:${RESET}\n"
DAILY_DIR="$MEMORY_DIR/daily"
if [ -d "$DAILY_DIR" ] && ls "$DAILY_DIR"/*.md >/dev/null 2>&1; then
    ls -1t "$DAILY_DIR"/*.md 2>/dev/null | head -7 | while read -r FILE; do
        DAY=$(basename "$FILE" .md)
        LINES=$(wc -l < "$FILE" | xargs)
        TASKS=$(grep -c "^Task:" "$FILE" 2>/dev/null || echo 0)
        FMOD=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$FILE" 2>/dev/null || echo "")
        FAGO=""
        [ -n "$FMOD" ] && FAGO="  last write $(time_ago "$FMOD")"
        printf "    ${BOLD}%s${RESET}  %s lines, %s tasks${DIM}%s${RESET}\n" "$DAY" "$LINES" "$TASKS" "$FAGO"
    done
    echo

    # Today's memory in detail
    TODAY="$DAILY_DIR/$(date +%Y-%m-%d).md"
    if [ -f "$TODAY" ]; then
        printf "  ${BOLD}Today's log (last 10 entries):${RESET}\n"
        # Show last entries (each entry starts with "Task:")
        grep -n "^Task:" "$TODAY" 2>/dev/null | tail -10 | while read -r LINE; do
            printf "    ${DIM}%s${RESET}\n" "$LINE"
        done
    fi
else
    printf "    ${DIM}No daily observations yet${RESET}\n"
fi

# ── 5. Scheduled Jobs ──────────────────────────────────────────────
section "SCHEDULED JOBS"

# Check crontab
CRON_JOBS=$(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' || true)
if [ -n "$CRON_JOBS" ]; then
    printf "  ${BOLD}Crontab entries:${RESET}\n"
    echo "$CRON_JOBS" | while read -r JOB; do
        printf "    ${GREEN}⏰${RESET} %s\n" "$JOB"
    done
else
    printf "  ${DIM}No crontab entries${RESET}\n"
fi

# Check LaunchAgents
echo
AGENTS=$(ls ~/Library/LaunchAgents/com.agentkit.*.plist 2>/dev/null || true)
if [ -n "$AGENTS" ]; then
    printf "  ${BOLD}LaunchAgents:${RESET}\n"
    for PLIST in $AGENTS; do
        LABEL=$(basename "$PLIST" .plist)
        LOADED=$(launchctl list 2>/dev/null | grep "$LABEL" || true)
        if [ -n "$LOADED" ]; then
            printf "    ${GREEN}● %s${RESET} (loaded)\n" "$LABEL"
        else
            printf "    ${RED}○ %s${RESET} (not loaded)\n" "$LABEL"
        fi
    done
else
    printf "  ${DIM}No agentkit LaunchAgents${RESET}\n"
fi

# ── 6. Context Preview ─────────────────────────────────────────────
section "CONTEXT (what the agent sees)"

SECTIONS=0

RECENT=$(ls -1t "$DAILY_DIR"/*.md 2>/dev/null | head -3)
if [ -n "$RECENT" ]; then
    RECENT_SIZE=0
    for F in $RECENT; do RECENT_SIZE=$((RECENT_SIZE + $(wc -c < "$F" | xargs))); done
    printf "  ${GREEN}✓${RESET} Recent context (3-day orientation): ~%s bytes\n" "$RECENT_SIZE"
    SECTIONS=$((SECTIONS + 1))
fi

if [ -f "$PROFILE_DIR/identity.md" ]; then
    SIZE=$(wc -c < "$PROFILE_DIR/identity.md" | xargs)
    printf "  ${GREEN}✓${RESET} Identity: %s bytes\n" "$SIZE"
    SECTIONS=$((SECTIONS + 1))
fi

if [ -f "$PROFILE_DIR/tools.md" ]; then
    SIZE=$(wc -c < "$PROFILE_DIR/tools.md" | xargs)
    printf "  ${GREEN}✓${RESET} Tools: %s bytes\n" "$SIZE"
    SECTIONS=$((SECTIONS + 1))
fi

if [ -f "$LTM" ]; then
    SIZE=$(wc -c < "$LTM" | xargs)
    printf "  ${GREEN}✓${RESET} Long-term memory: %s bytes\n" "$SIZE"
    SECTIONS=$((SECTIONS + 1))
fi

TOTAL_CTX=0
for F in "$PROFILE_DIR/identity.md" "$PROFILE_DIR/tools.md" "$LTM"; do
    [ -f "$F" ] && TOTAL_CTX=$((TOTAL_CTX + $(wc -c < "$F" | xargs)))
done
echo
printf "  ${BOLD}System prompt sections: %s${RESET}  ~%s bytes total context\n" "$SECTIONS" "$TOTAL_CTX"

# ── 7. Log Tail ────────────────────────────────────────────────────
section "RECENT LOG ($LOG_LINES lines)"

if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(wc -c < "$LOG_FILE" | xargs)
    LOG_TOTAL=$(wc -l < "$LOG_FILE" | xargs)
    LOG_MOD=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$LOG_FILE" 2>/dev/null || echo "")
    LOG_AGO=""
    [ -n "$LOG_MOD" ] && LOG_AGO=", last write $(time_ago "$LOG_MOD")"
    printf "  ${DIM}%s lines, %s bytes%s${RESET}\n\n" "$LOG_TOTAL" "$LOG_SIZE" "$LOG_AGO"

    tail -"$LOG_LINES" "$LOG_FILE" | while read -r LINE; do
        # Colorize log levels
        case "$LINE" in
            *ERROR*|*FAILED*|*failed*)
                printf "  ${RED}%s${RESET}\n" "$LINE" ;;
            *WARNING*|*WARN*)
                printf "  ${YELLOW}%s${RESET}\n" "$LINE" ;;
            *INFO*processing*|*Processing*)
                printf "  ${BLUE}%s${RESET}\n" "$LINE" ;;
            *completed*|*INFO*Task*)
                printf "  ${GREEN}%s${RESET}\n" "$LINE" ;;
            *)
                printf "  ${DIM}%s${RESET}\n" "$LINE" ;;
        esac
    done
else
    printf "  ${DIM}No log file at %s${RESET}\n" "$LOG_FILE"
fi

echo
divider
printf "${DIM}  Tip: 'make spy' refreshes every 5s  |  'make status' for one-shot  |  'make spy LOG=50' for more log lines${RESET}\n"
echo

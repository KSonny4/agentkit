#!/usr/bin/env bash
# spy-report.sh — ask a separate Claude agent to report on the running task
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$PROJECT_ROOT/data/agentkit.db"
PROGRESS="$PROJECT_ROOT/data/progress.jsonl"

BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

# Get the current task from DB
TASK_CONTENT=""
if [ -f "$DB" ]; then
    TASK_CONTENT=$(sqlite3 "$DB" "SELECT content FROM tasks WHERE status='processing' ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "")
fi

if [ -z "$TASK_CONTENT" ]; then
    # Try last completed/failed task
    TASK_CONTENT=$(sqlite3 "$DB" "SELECT content FROM tasks ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "unknown task")
fi

# Get progress events
PROGRESS_SUMMARY=""
if [ -f "$PROGRESS" ] && [ -s "$PROGRESS" ]; then
    PROGRESS_SUMMARY=$(python3 -c "
import json

tool_calls = []
texts = []
result_text = None
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
            result_text = e.get('result', '')[:300]
        elif t == 'assistant':
            msg = e.get('message', {})
            for block in msg.get('content', []):
                bt = block.get('type', '')
                if bt == 'tool_use':
                    name = block.get('name', '?')
                    inp = block.get('input', {})
                    tool_calls.append(f'{name}({json.dumps(inp)[:80]})')
                elif bt == 'text':
                    txt = block.get('text', '').strip()
                    if txt:
                        texts.append(txt[:200])
    except:
        pass

print(f'Total events: {total}')
print(f'Tool calls ({len(tool_calls)}):')
for tc in tool_calls[-15:]:
    print(f'  - {tc}')
if texts:
    print(f'Last text output:')
    print(texts[-1][:300])
if result_text:
    print(f'Final result: {result_text}')
" 2>/dev/null || echo "Could not parse progress file")
else
    printf "${RED}No progress file found. Is the agent running?${RESET}\n"
    exit 1
fi

printf "${BOLD}${CYAN}Asking Claude to analyze agent progress...${RESET}\n\n"

# Use a separate Claude instance to summarize
claude -p --model claude-opus-4-6 --allowedTools "Read,Glob,Grep" "$(cat <<EOF
You are a monitoring agent. Another AI agent was given a task and is working on it.
Analyze the progress data below and give a brief, clear report:

1. What was the task?
2. What has the agent done so far? (list key actions)
3. Is it still working or finished?
4. Any problems or concerns?

Keep it short — bullet points, no fluff.

## Task Given
$TASK_CONTENT

## Progress Events
$PROGRESS_SUMMARY
EOF
)"

# /add-playground

Adds a playground profile and smoke test script for end-to-end testing with real Claude CLI.

## What This Skill Does

- Creates `profiles/playground/identity.md`, `tools.md`, `evaluation.md`
- Creates `scripts/smoke-test.sh` with real E2E tests
- Adds `playground` and `smoke` targets to Makefile
- Makes smoke-test.sh executable

## Steps

### 1. Create `profiles/playground/identity.md`

```markdown
# Playground Agent

You are a helpful assistant used for testing and development of the agentkit framework.

## Behavior
- Answer questions clearly and concisely
- Follow instructions precisely
- When asked to remember something, use the MEMORY: prefix
- When asked to test features, be thorough

## Constraints
- This is a test environment — be helpful but cautious
- Do not make assumptions about production configuration
```

### 2. Create `profiles/playground/tools.md`

```markdown
# Available Tools

- **shell**: Execute shell commands (read-only by default)
- **Read/Glob/Grep**: Search and read files in the project
- **WebSearch/WebFetch**: Search the web for information

Note: Write tools (Edit, Write, Bash write) are only available in READWRITE mode (--write flag).
```

### 3. Create `profiles/playground/evaluation.md`

```markdown
# Evaluation Cycle

Review the current state of the agentkit project and provide a brief assessment:

1. **Health Check**: Are all tests passing? Any obvious issues?
2. **Memory Review**: Read recent daily memory. Any patterns or recurring issues?
3. **Improvement Ideas**: Suggest one concrete, small improvement.

Format your response as:
- Status: [healthy/degraded/broken]
- Summary: [1-2 sentences]
- MEMORY: [any observations worth remembering]
```

### 4. Create `scripts/smoke-test.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Smoke test — runs real E2E tests with Claude CLI
# Requires: claude CLI installed and authenticated

PASS=0
FAIL=0

run_test() {
    local name="$1"
    local cmd="$2"
    printf "  %-40s" "$name"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "PASS"
        ((PASS++))
    else
        echo "FAIL"
        ((FAIL++))
    fi
}

echo "=== agentkit smoke tests ==="
echo ""

# Test 1: CLI is available
run_test "CLI --help" "python -m agentkit task --help"

# Test 2: Unit tests pass
run_test "pytest" "python -m pytest -q"

# Test 3: Lint passes
run_test "ruff check" "ruff check ."

# Test 4: Task command runs (real Claude)
run_test "task: simple prompt" "python -m agentkit task 'Say hello in one word'"

# Test 5: Task with --write flag parses
run_test "task: --write flag" "python -m agentkit task --write 'Say hello in one word'"

# Test 6: Evaluate command runs (requires playground profile)
run_test "evaluate: playground" "python -m agentkit evaluate --profile playground"

# Test 7: Memory was updated
run_test "memory: daily file exists" "ls memory/daily/*.md"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
```

### 5. Add Makefile targets

Add to Makefile:

```makefile
playground:
	python -m agentkit task --profile playground "Hello! Run a quick self-check."

smoke:
	bash scripts/smoke-test.sh
```

### 6. Make executable

```bash
chmod +x scripts/smoke-test.sh
```

### 7. Verify

Run `pytest -v` to confirm existing tests still pass.
Run `make smoke` for full E2E test (requires Claude CLI).

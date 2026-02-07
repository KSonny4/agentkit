# /add-profile

Scaffolds a new custom agent profile for your agentkit fork.

## What This Skill Does

Interactively creates a complete profile directory with identity, tools, and evaluation templates.

## Steps

### 1. Ask the user for profile details

Ask the user:
- **Profile name**: What should this agent be called? (e.g., "trading", "game-monitor", "code-reviewer")
- **Purpose**: What does this agent do? What is its primary function?
- **Tools**: What tools does this agent need access to? (e.g., web search, shell commands, specific APIs)
- **Evaluation criteria**: How should this agent's performance be evaluated?

### 2. Create `profiles/{name}/identity.md`

Based on the user's description, create an identity file:

```markdown
# {Name} Agent

{User's description of who the agent is and what it does}

## Behavior
- {Specific behavioral guidelines based on purpose}
- Follow instructions precisely
- When observations are worth remembering, use the MEMORY: prefix

## Constraints
- {Any constraints relevant to this agent's domain}
```

### 3. Create `profiles/{name}/tools.md`

Based on the user's tool requirements:

```markdown
# Available Tools

{List of tools the agent needs, based on user input}

- **shell**: Execute shell commands
- **Read/Glob/Grep**: Search and read files
- {Any domain-specific tools}
```

### 4. Create `profiles/{name}/evaluation.md`

Based on the user's evaluation criteria:

```markdown
# Evaluation Cycle

{Evaluation template based on user's criteria}

1. **Health Check**: {Domain-specific health check}
2. **Performance Review**: {What to measure}
3. **Improvement Ideas**: Suggest one concrete improvement.

Format your response as:
- Status: [healthy/degraded/broken]
- Summary: [1-2 sentences]
- MEMORY: [any observations worth remembering]
```

### 5. Confirm

Print:
```
Profile '{name}' created at profiles/{name}/
Files:
  - profiles/{name}/identity.md
  - profiles/{name}/tools.md
  - profiles/{name}/evaluation.md

Run: agentkit task --profile {name} 'test prompt'
```

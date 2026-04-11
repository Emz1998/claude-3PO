# Plan: Convert claudeguard to Claude Code Plugin

## Context

The claudeguard hook system enforces phase-based workflow rules for the `/implement` skill. It currently lives at `claudeguard/scripts/` with hooks split between skill frontmatter and `settings.local.json`. Converting to a plugin consolidates everything — hooks, phase commands, agents — into a self-contained, shareable package.

## Steps

### 1. Create plugin manifest

Create `claudeguard/.claude-plugin/plugin.json`:
```json
{
  "name": "claudeguard",
  "version": "1.0.0",
  "description": "Phase-enforced guardrail system for structured implementation workflows"
}
```

### 2. Create `hooks/hooks.json`

Create `claudeguard/hooks/hooks.json` with all 5 hook events:
- `PreToolUse` → `${CLAUDE_PLUGIN_ROOT}/scripts/pre_tool_use.py` (10s)
- `PostToolUse` → `${CLAUDE_PLUGIN_ROOT}/scripts/post_tool_use.py` (10s)
- `SubagentStart` → `${CLAUDE_PLUGIN_ROOT}/scripts/subagent_start.py` (10s)
- `SubagentStop` → `${CLAUDE_PLUGIN_ROOT}/scripts/subagent_stop.py` (10s)
- `Stop` → `${CLAUDE_PLUGIN_ROOT}/scripts/stop.py` (10s)

### 3. Copy phase commands → `commands/`

Copy all 12 phase commands + implement.md from `.claude/commands/` → `claudeguard/commands/`:

| Source | Plugin path |
|---|---|
| `.claude/commands/implement.md` | `commands/implement.md` |
| `.claude/commands/explore.md` | `commands/explore.md` |
| `.claude/commands/research.md` | `commands/research.md` |
| `.claude/commands/plan.md` | `commands/plan.md` |
| `.claude/commands/plan-review.md` | `commands/plan-review.md` |
| `.claude/commands/write-tests.md` | `commands/write-tests.md` |
| `.claude/commands/test-review.md` | `commands/test-review.md` |
| `.claude/commands/write-code.md` | `commands/write-code.md` |
| `.claude/commands/quality-check.md` | `commands/quality-check.md` |
| `.claude/commands/code-review.md` | `commands/code-review.md` |
| `.claude/commands/pr-create.md` | `commands/pr-create.md` |
| `.claude/commands/ci-check.md` | `commands/ci-check.md` |
| `.claude/commands/write-report.md` | `commands/write-report.md` |

**Changes to `implement.md` only:**
- Remove the `hooks:` block from frontmatter
- Update initializer: `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/utils/initializer.py implement ${CLAUDE_SESSION_ID} $ARGUMENTS`
- Update project_manager: `[ -f "$CLAUDE_PROJECT_DIR/github_project/project_manager.py" ] && python3 "$CLAUDE_PROJECT_DIR/github_project/project_manager.py" view $0 || echo "No story context available"`

All other commands are copied as-is (no changes needed).

### 4. Copy agents → `agents/`

Copy the 6 agents used by the workflow from `.claude/agents/` → `claudeguard/agents/`:

| Source | Plugin path |
|---|---|
| `.claude/agents/planning/research.md` | `agents/research.md` |
| `.claude/agents/planning/plan-review.md` | `agents/plan-review.md` |
| `.claude/agents/quality-assurance/test-reviewer.md` | `agents/test-reviewer.md` |
| `.claude/agents/quality-assurance/qa-specialist.md` | `agents/qa-specialist.md` |
| `.claude/agents/quality-assurance/code-reviewer.md` | `agents/code-reviewer.md` |
| `.claude/agents/devops/version-manager.md` | `agents/version-manager.md` |

Agents are copied as-is. Note: Explore is a built-in agent, not copied.

**Important**: Plugin agents do NOT support `hooks`, `mcpServers`, or `permissionMode` in frontmatter (per plugin docs). Verify none of these agents use those fields.

### 5. Remove claudeguard entries from `settings.local.json`

Remove these two entries:
- `SubagentStart` → `./scripts/subagent_start.py` (lines ~139-147)
- `SubagentStop` → `./scripts/subagent_stop.py` (lines ~168-176)

### 6. Ensure scripts are executable

```bash
chmod +x claudeguard/scripts/{pre_tool_use,post_tool_use,subagent_start,subagent_stop,stop}.py
```

### No Python changes needed

All entry points resolve paths via `Path(__file__).resolve().parent`. State, config, and module imports all resolve relative to the script's filesystem location.

## Final structure

```
claudeguard/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── implement.md
│   ├── explore.md
│   ├── research.md
│   ├── plan.md
│   ├── plan-review.md
│   ├── write-tests.md
│   ├── test-review.md
│   ├── write-code.md
│   ├── quality-check.md
│   ├── code-review.md
│   ├── pr-create.md
│   ├── ci-check.md
│   └── write-report.md
├── agents/
│   ├── research.md
│   ├── plan-review.md
│   ├── test-reviewer.md
│   ├── qa-specialist.md
│   ├── code-reviewer.md
│   └── version-manager.md
├── hooks/
│   └── hooks.json
└── scripts/
    ├── pre_tool_use.py
    ├── post_tool_use.py
    ├── subagent_start.py
    ├── subagent_stop.py
    ├── stop.py
    ├── state.json
    ├── config/ constants/ models/ guardrails/ utils/ tests/
```

## Verification

1. Run existing tests: `cd claudeguard && pytest scripts/tests/` — should pass unchanged
2. Load plugin: `claude --plugin-dir ./claudeguard`
3. Verify `/claudeguard:implement` appears in skills list
4. Verify agents appear in `/agents` (Research, PlanReview, TestReviewer, etc.)
5. Smoke test: invoke the skill, confirm hooks fire
6. Confirm `settings.local.json` no longer has claudeguard entries

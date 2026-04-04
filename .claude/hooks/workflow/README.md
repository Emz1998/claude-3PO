# Workflow Guardrail

Enforces a structured multi-phase development workflow by validating Claude Code tool invocations against shared state. Each phase must complete before the next can begin, with automated phase progression and review gates.

---

## Architecture

```
guardrail.py          ← CLI entry point; dispatches to guards
guards/
  agent_guard.py      ← agent allowlists, max counts, ordering rules
  phase_guard.py      ← enforces phase order on Skill invocations
  write_guard.py      ← blocks code writes until plan/tests complete
  bash_guard.py       ← blocks git push until all phases done
  review_guard.py     ← handles SubagentStop, parses scores, auto-advances
  stop_guard.py       ← blocks session stop until workflow complete
state_store.py        ← JSON persistence with file locking
dispatchers/
  pre_tool_use.py     ← reads stdin, calls guardrail, blocks if needed
dry_run.py            ← end-to-end workflow simulator
tests/                ← pytest test suite
```

---

## Workflow Phases

Phases must complete in order:

```
explore → decision → plan → [write-tests] → write-code → validate → pr-create
                               TDD only
```

Each phase is represented in state as `pending | in_progress | completed | failed`.

---

## Guards

| Guard | Trigger | What it blocks |
|-------|---------|----------------|
| `phase_guard` | Skill tool | Out-of-order phase transitions |
| `agent_guard` | Agent tool | Wrong agent type for phase, exceeding max count, ordering violations |
| `write_guard` | Write / Edit | Code file writes before plan complete (and tests if TDD) |
| `bash_guard` | Bash tool | `git push` / `gh pr create` until all phases done |
| `review_guard` | SubagentStop | Never blocks — marks agents complete, parses scores, auto-advances phases |
| `stop_guard` | Stop event | Session stop while any phase is incomplete |

### Phase agents and completion criteria

| Phase | Allowed agents | Completes when |
|-------|---------------|---------------|
| `explore` | `codebase-explorer` (max 3), `research-specialist` (max 2) | 3 explorers + 2 specialists complete |
| `decision` | `tech-lead` (max 1) | 1 tech-lead completes |
| `plan` | `plan-specialist` → `plan-reviewer` | Reviewer scores ≥ 80 confidence + 80 quality |
| `write-tests` | `test-engineer` → `test-reviewer` | Reviewer scores ≥ 80/80 (TDD only) |
| `write-code` | *(no subagents — main agent writes directly)* | Manually advanced |
| `validate` | `qa-expert` (max 1) | 1 qa-expert completes |
| `pr-create` | `version-manager` (max 1) | 1 version-manager completes |

---

## State Structure

`state.json` (default path: `.claude/hooks/workflow/state.json`):

```json
{
  "workflow_active": true,
  "TDD": false,
  "session_id": "uuid",
  "story_id": "SK-001",
  "phases": [
    {
      "name": "explore",
      "status": "completed",
      "agents": [
        {"agent_type": "codebase-explorer", "status": "completed", "tool_use_id": "t1"},
        {"agent_type": "research-specialist", "status": "completed", "tool_use_id": "t2"}
      ],
      "files_created": []
    }
  ],
  "review": {
    "plan": {
      "status": "approved",
      "iteration": 0,
      "max_iterations": 3,
      "scores": {"confidence": 85, "quality": 90},
      "threshold": {"confidence": 80, "quality": 80}
    },
    "tests": { "..." : "..." }
  }
}
```

Override the state path with `GUARDRAIL_STATE_PATH=/custom/path.json`.

---

## Usage

### Hook integration

Wire the dispatcher as a Claude Code hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/workflow/dispatchers/pre_tool_use.py"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/workflow/dispatchers/pre_tool_use.py"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/workflow/dispatchers/pre_tool_use.py"}]}]
  }
}
```

### Manual CLI

```bash
# Check a hook payload
python3 guardrail.py --hook-input '{"hook_event_name":"PreToolUse","tool_name":"Skill",...}'

# Print block reason
python3 guardrail.py --hook-input '...' --reason

# Manually advance next pending phase to in_progress
python3 guardrail.py --advance

# Custom state path
GUARDRAIL_STATE_PATH=/tmp/test-state.json python3 guardrail.py --hook-input '...'
```

Output: `allow` or `block` (with `block, <reason>` when `--reason` is set).

### Dry-run simulator

Replays real hook payloads through guardrail.py to verify all guards work end-to-end:

```bash
# Non-TDD (write-tests phase skipped)
python3 .claude/hooks/workflow/dry_run.py

# TDD mode (includes write-tests phase)
python3 .claude/hooks/workflow/dry_run.py --tdd
```

Output: color-coded `PASS` (green) / `BLOCK` (red, expected) / `FAIL` (red, unexpected) for each step, with a summary at the end. Each step includes a 5-second delay to simulate real agent execution.

### Tests

```bash
cd .claude/hooks/workflow
pytest tests/
```

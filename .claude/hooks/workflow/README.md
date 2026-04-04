# Workflow Guardrail

Enforces a structured multi-phase development workflow by validating Claude Code tool invocations against session-scoped state. Each phase must complete before the next can begin, with automated phase progression and review gates.

---

## Architecture

```
guardrail.py              <- CLI entry; dispatches to guards, returns allow/block
recorder.py               <- CLI entry; all state mutations (phase advances, agent tracking)
session_store.py           <- JSONL-backed session-scoped state (replaces state_store.py)
reminder.py                <- Read-only phase-aware context injection
hook.py                    <- Shared hook I/O helpers (stdin, stdout, block, send_context)
auto_commit.py             <- Async hook; auto-commits after TaskCompleted via headless Claude
guards/
  agent_guard.py           <- Agent allowlists, max counts per phase
  write_guard.py           <- Blocks code writes outside coding phases; validates plan template
  bash_guard.py            <- Blocks PR/push commands until ready; validates commit format
  read_guard.py            <- Plan-scoped file reads during coding phases
  stop_guard.py            <- Blocks session stop until workflow complete
  skill_guard.py           <- Intercepts /plan and /implement; initializes workflow state
  task_guard.py            <- Validates TaskCreate maps to real project tasks
  webfetch_guard.py        <- Domain whitelist for WebFetch
  subagent_stop_guard.py   <- Validates agent output schema (e.g. Validator report format)
dispatchers/
  pre_tool_use.py          <- PreToolUse: guardrail + recorder + reminders
  post_tool_use.py         <- PostToolUse: recorder + reminders
  session_start.py         <- SessionStart: cleanup inactive sessions, advance after plan approval
  subagent_start.py        <- SubagentStart: inject agent-role reminders
  subagent_stop.py         <- SubagentStop: guardrail + recorder + phase transition reminders
  user_prompt_submit.py    <- UserPromptSubmit: skill activation + explore kickoff
config/
  paths.py                 <- DEFAULT_STATE_JSONL_PATH, COMMIT_BATCH_PATH, etc.
  constants.py             <- Phase sets, agent limits, review thresholds, patterns
dry_runs/
  plan_dry_run.py          <- End-to-end /plan workflow simulator
  implement_dry_run.py     <- End-to-end /implement workflow simulator
tests/                     <- pytest test suite (361 tests)
```

---

## Workflow Phases

### /plan workflow

```
explore -> write-codebase -> plan -> write-plan -> review -> present-plan
```

### /implement workflow

```
explore -> write-codebase -> plan -> write-plan -> review -> present-plan ->
  [task-create] -> [write-tests] -> write-code -> validate ->
  pr-create -> ci-check -> report -> completed
```

- `task-create`: only when a story ID is provided
- `write-tests`: only when `--tdd` flag is used

---

## Guards

| Guard | Trigger | What it blocks |
|-------|---------|----------------|
| `skill_guard` | PostToolUse(Skill), UserPromptSubmit | Activates workflow state on /plan or /implement |
| `agent_guard` | PreToolUse(Agent) | Wrong agent type for phase, exceeding max count |
| `write_guard` | PreToolUse(Write/Edit) | Code writes outside coding phases; invalid plan template |
| `read_guard` | PreToolUse(Read) | Reads outside plan-listed files during coding phases |
| `bash_guard` | PreToolUse(Bash) | PR/push before validation; invalid commit format |
| `webfetch_guard` | PreToolUse(WebFetch) | Non-whitelisted domains |
| `task_guard` | PreToolUse(TaskCreate), TaskCompleted | Tasks without valid project task metadata |
| `stop_guard` | Stop | Session stop while workflow incomplete |
| `subagent_stop_guard` | SubagentStop | Agent output missing required report sections |

### Phase agents and limits

| Phase | Allowed agents | Max | Completes when |
|-------|---------------|-----|---------------|
| `explore` | Explore | 3 | All Explore + Research agents complete |
| `explore` | Research | 2 | (combined with above) |
| `plan` | Plan | 1 | Plan agent completes -> write-plan |
| `review` | PlanReview | 3 | Scores >= 80 confidence + 80 quality |
| `write-tests` | TestReviewer | 3 | TestReviewer returns Pass |
| `validate` | Validator | 1 | Validator returns Pass -> pr-create |

### Phase gate

During `explore` and `plan` phases, only the Agent tool is allowed from the main agent (phase gate). During `review`, Agent + Write/Edit are allowed. Subagent calls always bypass the phase gate.

---

## State

### Session-scoped JSONL

State is stored in `state.jsonl` (one JSON line per session, keyed by `session_id`):

```jsonl
{"session_id":"abc-123","workflow_active":true,"workflow_type":"implement","phase":"write-code","story_id":"SK-001","agents":[...],...}
{"session_id":"def-456","workflow_active":true,"workflow_type":"plan","phase":"explore",...}
```

Each session is fully isolated — guards only see their own session's state. This means:
- Multiple workflows can run concurrently
- Headless sessions (auto_commit) are not blocked by another session's phase restrictions
- Inactive sessions (`workflow_active: false`) are auto-cleaned on each SessionStart

Override the state path with `GUARDRAIL_STATE_PATH` or `RECORDER_STATE_PATH` env vars.

### Key state fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | str | Claude session UUID (auto-injected) |
| `workflow_active` | bool | Whether guardrails are enforced |
| `workflow_type` | str | `"implement"` or `"plan"` |
| `phase` | str | Current workflow phase |
| `agents` | list | Running/completed agent entries |
| `plan_file` | str | Path to the written plan |
| `plan_written` | bool | Whether plan file exists |
| `plan_review_iteration` | int | Current review iteration |
| `plan_review_scores` | dict | `{confidence, quality}` |
| `plan_review_status` | str | `approved`, `revision_needed`, `max_iterations_reached` |
| `validation_result` | str | `Pass` or `Fail` |
| `pr_status` | str | `pending` or `created` |
| `ci_status` | str | `pending`, `passed`, `failed` |

---

## Usage

### Hook integration

Dispatchers are wired as Claude Code hooks in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/session_start.py"}]}],
    "PreToolUse": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/pre_tool_use.py"}]}],
    "PostToolUse": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/post_tool_use.py"}]}],
    "SubagentStart": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/subagent_start.py"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/subagent_stop.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/user_prompt_submit.py"}]}]
  }
}
```

### Manual CLI

```bash
# Check a hook payload against guardrail
python3 guardrail.py --hook-input '{"hook_event_name":"PreToolUse","tool_name":"Agent",...}' --reason

# Record a state change
python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse","tool_name":"Write",...}'
```

Output: `allow` or `block, <reason>`.

### Dry-run simulators

Replay full workflows through guardrail + recorder to verify all guards work end-to-end:

```bash
# Plan workflow
python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py
python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-all

# Implement workflow
python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py
python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd
python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd --story-id SK-001
```

### Tests

```bash
pytest .claude/hooks/workflow/tests/
```

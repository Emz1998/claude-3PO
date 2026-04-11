# Scripts — Workflow Hook System

Guardrail system that enforces phase-based rules for Claude Code hooks.

## Architecture

```
stdin (JSON) --> Entry Points --> Guardrails --> Validators (check)
                                            --> Recorders  (write state)
                                            --> Resolvers  (advance state)
                                            --> stdout (JSON decision)
```

### Entry Points

| File | Hook Event | Purpose |
|---|---|---|
| `pre_tool_use.py` | PreToolUse | Blocks disallowed tool calls before execution |
| `post_tool_use.py` | PostToolUse | Records results after Bash commands (PR, CI, tests) |
| `subagent_stop.py` | SubagentStop | Validates agent reports (scores/verdicts) from `last_assistant_message` |

### Guardrails (`guardrails/`)

Handlers that wire validators to recorders. Each returns `("allow", msg)` or `("block", msg)`.

| Guard | Tool | What it checks |
|---|---|---|
| `write_guard` | Write | Phase allows writes, file path is valid |
| `edit_guard` | Edit | Phase allows edits, file was written this session |
| `command_guard` | Bash | Command is whitelisted for current phase |
| `agent_guard` | Agent | Agent matches phase requirement, under max count |
| `webfetch_guard` | WebFetch | URL domain is in safe list |
| `phase_guard` | Skill | Phase transition follows ordering rules |
| `agent_report_guard` | (Stop) | Agent response has valid scores or verdict |

### Validators (`utils/validators.py`)

Pure validation — check conditions, return `tuple[bool, str]` or raise `ValueError`. Never mutate state.

### Recorders (`utils/recorder.py`)

Write raw data to `state.json`. Called by guardrails after validation passes.

### Resolvers (`utils/resolvers.py`)

Evaluate state after recording and advance the workflow:
- Complete phases when conditions are met
- Start sub-phases (revisions) when review scores are below threshold
- Increment review iterations

### State (`state.json`)

Single JSON file tracking workflow progress: phases, agents, plan, tests, code files, PR, CI status.

### Config (`config/config.toml`)

Phase classifications, agent limits, score thresholds, safe domains, file paths.

### Constants (`constants/constants.py`)

Command whitelists (PR, CI, install, test, read-only), file patterns, code extensions.

### Models (`models/state.py`)

Pydantic models mirroring the `state.json` schema.

## Data Flow

```
PreToolUse:   validate --> record --> respond (allow/block)
PostToolUse:  record output --> resolve state
SubagentStop: validate report --> record scores/verdict --> resolve state
```

## Phase Lifecycle

```
explore --> research --> plan --> plan-review --> write-tests --> test-review
--> write-code --> quality-check --> code-review --> pr-create --> ci-check --> write-report
```

Review phases (`plan-review`, `test-review`, `code-review`) can trigger sub-phases (`plan-revision`, `refactor`) when scores are below threshold.

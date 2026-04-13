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
| `post_tool_use.py` | PostToolUse | Records results after Bash commands (PR, CI, tests), auto-parses plan sections |
| `subagent_stop.py` | SubagentStop | Validates agent reports (scores/verdicts), checkpoints on plan-review pass |
| `task_created.py` | TaskCreated | Validates task subjects match planned tasks from `## Tasks` |
| `stop.py` | Stop | Blocks stop until all phases are completed |

### Guardrails (`guardrails/`)

Handlers that wire validators to recorders. Each returns `("allow", msg)` or `("block", msg)`.

| Guard | Tool | What it checks |
|---|---|---|
| `write_guard` | Write | Phase allows writes, file path is valid, plan content follows template |
| `edit_guard` | Edit | Phase allows edits, file was written this session, plan edits preserve required sections |
| `command_guard` | Bash | Command is whitelisted for current phase |
| `agent_guard` | Agent | Agent matches phase requirement, under max count |
| `webfetch_guard` | WebFetch | URL domain is in safe list |
| `phase_guard` | Skill | Phase transition follows ordering rules |
| `agent_report_guard` | (Stop) | Agent response has valid scores or verdict |

### Validators (`utils/validators.py`)

Pure validation — check conditions, return `tuple[bool, str]` or raise `ValueError`. Never mutate state.

Key validations:
- **Plan content**: required `## Dependencies`, `## Contracts`, `## Tasks` sections with bullet format (no `###` subsections)
- **Plan edit**: edits must not remove required sections
- **Install-deps**: only package manager files (`package.json`, `requirements.txt`, etc.)
- **Define-contracts**: only code extension files

### Recorders (`utils/recorder.py`)

Write raw data to `state.json`. Called by guardrails after validation passes.

Key recorders:
- `record_plan_sections()` — auto-extracts dependencies and tasks from plan on write
- `record_contracts_file()` — auto-extracts contract names from contracts.md on write
- `record_dependency_install()` — marks deps as installed when install command runs

### Resolvers (`utils/resolvers.py`)

Evaluate state after recording and advance the workflow:
- Complete phases when conditions are met
- Start sub-phases (revisions) when review scores are below threshold
- Increment review iterations

### State (`state.json`)

Single JSON file tracking workflow progress: phases, agents, plan, tasks, dependencies, contracts, tests, code files, PR, CI status.

### Config (`config/config.toml`)

Phase classifications, agent limits, score thresholds, safe domains, file paths (including contracts paths).

### Constants (`constants/constants.py`)

Command whitelists (PR, CI, install, test, read-only), file patterns, code extensions, package manager files.

### Models (`models/state.py`)

Pydantic models mirroring the `state.json` schema, including `Dependencies` and `Contracts` models.

### Templates (`templates/`)

| File | Purpose |
|---|---|
| `plan.md` | Plan template enforcing bullet format for Dependencies, Contracts, Tasks sections |

The plan template is enforced by `_validate_plan_content()` in the Write guardrail. Plans that use `###` subsections instead of `- bullet` items are rejected.

## Data Flow

```
PreToolUse:   validate --> record --> respond (allow/block)
PostToolUse:  record output --> auto-parse plan sections --> resolve state
SubagentStop: validate report --> record scores/verdict --> resolve state --> checkpoint
TaskCreated:  match task subject against planned tasks --> allow/block
```

## Phase Lifecycle

```
explore --> research --> plan --> plan-review --> install-deps --> define-contracts
--> write-tests --> test-review --> write-code --> quality-check --> code-review
--> pr-create --> ci-check --> write-report
```

### Checkpoints

- **plan-review pass**: `Hook.discontinue()` stops the workflow so the user can review the plan before proceeding to `install-deps`.

### Sub-phases

Review phases (`plan-review`, `test-review`, `code-review`) can trigger sub-phases (`plan-revision`, `refactor`) when scores are below threshold.

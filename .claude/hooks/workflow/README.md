# Workflow Hooks Architecture

This document describes the architecture and flow of the workflow hooks system used for orchestrating Claude Code development workflows.

## Overview

The workflow system enforces a structured development process through Claude Code hooks. It ensures:
- Phases execute in the correct order
- Only authorized subagents can perform phase-specific work
- Deliverables are tracked and required before phase transitions
- Release plan items (tasks, ACs, SCs) are validated and recorded

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLAUDE CODE HOOKS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│   │ UserPromptSubmit│     │   PreToolUse    │     │   PostToolUse   │       │
│   │     Handler     │     │     Handler     │     │     Handler     │       │
│   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘       │
│            │                       │                       │                 │
│            ▼                       ▼                       ▼                 │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│   │ Workflow        │     │     Guards      │     │    Trackers     │       │
│   │ Activation      │     │ ┌─────────────┐ │     │ ┌─────────────┐ │       │
│   │                 │     │ │PhaseTransit.│ │     │ │PhaseTracker │ │       │
│   └─────────────────┘     │ │SubagentAccs.│ │     │ │Deliverables │ │       │
│                           │ │ReleasePlan  │ │     │ │ReleasePlan  │ │       │
│                           │ └─────────────┘ │     │ └─────────────┘ │       │
│                           └────────┬────────┘     └────────┬────────┘       │
│                                    │                       │                 │
│                                    ▼                       ▼                 │
│                           ┌─────────────────────────────────────┐           │
│                           │           CORE MODULES              │           │
│                           │  ┌─────────────┐ ┌─────────────┐    │           │
│                           │  │StateManager │ │ PhaseEngine │    │           │
│                           │  └─────────────┘ └─────────────┘    │           │
│                           │  ┌─────────────┐ ┌─────────────┐    │           │
│                           │  │Deliverables │ │ReleasePlan  │    │           │
│                           │  │  Tracker    │ │   Module    │    │           │
│                           │  └─────────────┘ └─────────────┘    │           │
│                           └─────────────────────────────────────┘           │
│                                           │                                  │
│                                           ▼                                  │
│                           ┌─────────────────────────────────────┐           │
│                           │            STATE FILES              │           │
│                           │  state.json    workflow_config.json │           │
│                           │  project/state.json (release plan)  │           │
│                           └─────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
workflow/
├── README.md                 # This file
├── state.json                # Workflow state (active, phase, deliverables)
├── __init__.py               # Backward-compatible exports
│
├── config/
│   ├── workflow_config.json  # Phase definitions, subagent mappings, deliverables
│   └── loader.py             # Configuration loading with caching
│
├── core/
│   ├── state_manager.py      # Unified state API
│   ├── phase_engine.py       # Phase ordering and transitions
│   └── deliverables_tracker.py # Deliverable completion tracking
│
├── guards/                   # PreToolUse validation
│   ├── phase_transition.py   # Enforce phase order
│   ├── subagent_access.py    # Enforce subagent permissions
│   ├── read_order.py         # Enforce file read order (optional)
│   └── deliverables_exit.py  # Block phase exit without deliverables
│
├── trackers/                 # PostToolUse recording
│   ├── phase_tracker.py      # Record phase changes
│   ├── deliverables_tracker.py # Mark deliverables complete
│   └── release_plan_tracker.py # Validate & record release plan items
│
├── handlers/                 # Hook entry points
│   ├── pre_tool.py           # Routes PreToolUse to guards
│   ├── post_tool.py          # Routes PostToolUse to trackers
│   ├── user_prompt.py        # Handles UserPromptSubmit
│   └── subagent_stop.py      # Handles SubagentStop
│
├── context/                  # Context injection
│   ├── context_injector.py   # Inject reminders into responses
│   └── phase_reminders.py    # Phase-specific reminder content
│
├── release_plan/             # Release plan integration
│   ├── utils.py              # Find items (task, AC, SC, etc.)
│   ├── getters.py            # Get current items from state
│   ├── checkers.py           # Check completion status
│   ├── resolvers.py          # Record completed items
│   ├── new_setters.py        # Update state values
│   └── state.py              # Project state file operations
│
└── tests/
    ├── test_workflow_architecture.py
    └── test_release_plan_tracker.py
```

## Hook Event Flow

### 1. UserPromptSubmit

Triggered when user submits a prompt. Used for:
- Workflow activation via `/implement` command
- Workflow deactivation via `/deactivate-workflow`

### 2. PreToolUse (Validation Phase)

Triggered before any tool executes. **Blocks invalid operations.**

```
User invokes Skill tool (e.g., /plan)
           │
           ▼
┌─────────────────────────────────────────┐
│        PreToolHandler.run()             │
├─────────────────────────────────────────┤
│                                         │
│  1. Check workflow active               │
│     └─► If inactive: exit(0) allow      │
│                                         │
│  2. Route by tool_name:                 │
│                                         │
│     Skill tool:                         │
│     ├─► PhaseTransitionGuard            │
│     │   • Validate phase order          │
│     │   • Block skipping phases         │
│     │   • Block going backwards         │
│     │                                   │
│     └─► ReleasePlanTracker.run_pre_tool │
│         • Validate log:task ID exists   │
│         • Validate log:ac ID exists     │
│         • Validate log:sc ID exists     │
│                                         │
│     Task tool:                          │
│     └─► SubagentAccessGuard             │
│         • Validate subagent allowed     │
│         • Block unauthorized agents     │
│                                         │
│  3. All checks pass: exit(0)            │
│     Any check fails: exit(2) + stderr   │
│                                         │
└─────────────────────────────────────────┘
```

### 3. PostToolUse (Recording Phase)

Triggered after tool executes successfully. **Records state changes.**

```
Tool execution completes
           │
           ▼
┌─────────────────────────────────────────┐
│        PostToolHandler.run()            │
├─────────────────────────────────────────┤
│                                         │
│  1. Check workflow active               │
│     └─► If inactive: return             │
│                                         │
│  2. Route by tool_name:                 │
│                                         │
│     Skill tool:                         │
│     ├─► PhaseTracker                    │
│     │   • Update current_phase          │
│     │   • Record phase_history          │
│     │                                   │
│     ├─► ContextInjector                 │
│     │   • Inject phase reminders        │
│     │                                   │
│     ├─► DeliverableTracker              │
│     │   • Mark skill deliverables done  │
│     │                                   │
│     └─► ReleasePlanTracker.run_post_tool│
│         • Record completed tasks        │
│         • Record met ACs                │
│         • Record met SCs                │
│                                         │
│     Write/Edit/Read/Bash:               │
│     └─► DeliverableTracker              │
│         • Mark file deliverables done   │
│                                         │
└─────────────────────────────────────────┘
```

## Phase System

### Phase Order (TDD Strategy)

```
explore → plan → plan-consult → finalize-plan → write-test → review-test →
write-code → code-review → refactor → validate → commit
```

### Phase Order (Test-After Strategy)

```
explore → plan → plan-consult → finalize-plan → write-code → write-test →
review-test → code-review → refactor → validate → commit
```

### Phase-Subagent Mapping

| Phase          | Subagent           |
|----------------|-------------------|
| explore        | codebase-explorer |
| plan           | planner           |
| plan-consult   | plan-consultant   |
| finalize-plan  | planner           |
| write-test     | test-engineer     |
| review-test    | test-reviewer     |
| write-code     | main-agent        |
| code-review    | code-reviewer     |
| refactor       | main-agent        |
| validate       | validator         |
| commit         | version-manager   |

## Release Plan Integration

The `release_plan_tracker` validates and records release plan items:

### Validation (PreToolUse)

When user invokes `/log:task T001 completed`:

1. Parse arguments → `task_id="T001"`, `status="completed"`
2. Call `find_task("T001")` from `release_plan/utils.py`
3. If `None` → Block with "Task 'T001' not found in release plan"
4. If found → Allow execution

### Recording (PostToolUse)

After successful execution:

1. Parse arguments → same as above
2. If `log:task` + `completed` → `record_completed_task("T001")`
3. If `log:ac` + `met` → `record_met_ac("AC-001")`
4. If `log:sc` + `met` → `record_met_sc("SC-001")`

### Supported Commands

| Command | Valid Statuses | Recording |
|---------|---------------|-----------|
| `/log:task TXXX status` | not_started, in_progress, completed, blocked | Records on `completed` |
| `/log:ac AC-XXX status` | met, unmet | Records on `met` |
| `/log:sc SC-XXX status` | met, unmet | Records on `met` |

## State Management

### Workflow State (`state.json`)

```json
{
  "workflow_active": true,
  "current_phase": "plan",
  "deliverables": [
    {
      "type": "files",
      "action": "read",
      "pattern": ".*codebase-status.md$",
      "priority": 1,
      "completed": true
    },
    {
      "type": "files",
      "action": "write",
      "pattern": ".*plan.md$",
      "priority": 2,
      "completed": false
    }
  ],
  "phase_history": ["explore"],
  "dry_run_active": false
}
```

### Project State (`project/state.json`)

```json
{
  "current_epic_id": "E001",
  "current_feature_id": "F001",
  "current_user_story": "US-001",
  "current_tasks": {"T001": "in_progress", "T002": "not_started"},
  "current_acs": {"AC-001": "unmet"},
  "current_scs": {"SC-001": "unmet"},
  "completed_tasks": ["T000"],
  "completed_user_stories": [],
  "completed_features": [],
  "completed_epics": [],
  "met_acs": [],
  "met_scs": []
}
```

## Configuration

### `workflow_config.json`

```json
{
  "phases": {
    "base": ["explore", "plan", "plan-consult", "finalize-plan", "code", "commit"],
    "tdd": ["write-test", "review-test", "write-code", "code-review", "refactor", "validate"],
    "test-after": ["write-code", "write-test", "review-test", "code-review", "refactor", "validate"]
  },
  "subagents": {
    "explore": "codebase-explorer",
    "plan": "planner",
    ...
  },
  "deliverables": {
    "explore": [
      {"type": "files", "action": "read", "pattern": "prompt.md", "priority": 1},
      {"type": "files", "action": "write", "pattern": ".*codebase-status.md$", "priority": 2}
    ],
    ...
  },
  "required_read_order": ["recap.md", "ms-summary.md", "tasks.md", ...]
}
```

## Key Design Decisions

1. **Separation of Concerns**: Guards validate, trackers record, handlers route
2. **Exit Codes**: `0` = allow, `2` = block with error message
3. **Priority System**: Lower priority number = higher priority, must complete first
4. **Singleton Patterns**: StateManager and PhaseEngine use module-level singletons
5. **Backward Compatibility**: Legacy functions wrap new classes for smooth migration
6. **Release Plan Integration**: Real validation against release plan, not just regex patterns

## Testing

Run all tests:
```bash
python -m pytest .claude/hooks/workflow/tests/ -v
```

Run specific test file:
```bash
python -m pytest .claude/hooks/workflow/tests/test_release_plan_tracker.py -v
```

## Adding New Guards/Trackers

### New Guard (PreToolUse)

1. Create `guards/my_guard.py`:
```python
class MyGuard:
    def __init__(self):
        self._state = get_manager()

    def is_active(self) -> bool:
        return self._state.is_workflow_active()

    def run(self, hook_input: dict) -> None:
        if not self.is_active():
            return
        # Validation logic
        if invalid:
            print("Error message", file=sys.stderr)
            sys.exit(2)
```

2. Import and use in `handlers/pre_tool.py`

### New Tracker (PostToolUse)

1. Create `trackers/my_tracker.py`:
```python
class MyTracker:
    def __init__(self):
        self._state = get_manager()

    def is_active(self) -> bool:
        return self._state.is_workflow_active()

    def run(self, hook_input: dict) -> None:
        if not self.is_active():
            return
        # Recording logic (no exit codes)
```

2. Import and use in `handlers/post_tool.py`

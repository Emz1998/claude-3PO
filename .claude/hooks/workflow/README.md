# Workflow Hooks Architecture

This document describes the architecture and flow of the workflow hooks system used for orchestrating Claude Code development workflows.

## Overview

The workflow system enforces a structured development process through Claude Code hooks. It ensures:
- Phases execute in the correct order
- Only authorized subagents can perform phase-specific work
- Deliverables are tracked and required before phase transitions
- Release plan items (tasks, ACs, SCs) are validated and recorded
- Criteria validation is enforced at user story, feature, and epic boundaries
- Task DoD (Definition of Done) is enforced before agent stop

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
│   │ Activation +   │     │ ┌─────────────┐ │     │ ┌─────────────┐ │       │
│   │ Validation     │     │ │PhaseTransit.│ │     │ │PhaseTracker │ │       │
│   │ Detection      │     │ │SubagentAccs.│ │     │ │Deliverables │ │       │
│   └─────────────────┘     │ │ReleasePlan  │ │     │ │ReleasePlan  │ │       │
│                           │ └─────────────┘ │     │ └─────────────┘ │       │
│   ┌─────────────────┐     └────────┬────────┘     └────────┬────────┘       │
│   │      Stop       │              │                       │                 │
│   │     Handler     │              ▼                       ▼                 │
│   │ ┌─────────────┐ │    ┌─────────────────────────────────────┐           │
│   │ │TaskDodStop  │ │    │           CORE MODULES              │           │
│   │ └─────────────┘ │    │  ┌─────────────┐ ┌─────────────┐    │           │
│   └─────────────────┘    │  │StateManager │ │ PhaseEngine │    │           │
│                           │  └─────────────┘ └─────────────┘    │           │
│   ┌─────────────────┐    │  ┌─────────────┐ ┌─────────────┐    │           │
│   │   Validators    │    │  │Deliverables │ │ReleasePlan  │    │           │
│   │ ┌─────────────┐ │    │  │  Tracker    │ │   Module    │    │           │
│   │ │CriteriaVal. │ │    │  └─────────────┘ └─────────────┘    │           │
│   │ │RevisionMgr. │ │    │  ┌─────────────┐                     │           │
│   │ └─────────────┘ │    │  │  Auditor   │ -> logs/            │           │
│   └─────────────────┘    └─────────────────────────────────────┘           │
│                                            │                                  │
│                                            ▼                                  │
│                           ┌─────────────────────────────────────┐           │
│                           │            STATE FILES              │           │
│                           │  state.json    workflow.config.yaml │           │
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
│   ├── workflow.config.yaml      # Phase definitions, subagent mappings, deliverables
│   ├── unified_loader.py         # Configuration loading with caching and validation
│   └── WORKFLOW_CONFIG_GUIDE.md  # Configuration guide
│
├── core/
│   ├── state_manager.py      # Unified state API (includes pending_validation)
│   ├── phase_engine.py       # Phase ordering and transitions
│   ├── deliverables_tracker.py # Deliverable completion tracking
│   └── workflow_auditor.py   # Invariant checks and violation logging
│
├── guards/                   # PreToolUse + Stop validation
│   ├── phase_transition.py   # Enforce phase order
│   ├── subagent_access.py    # Enforce subagent permissions
│   ├── deliverables_exit.py  # Block phase exit without deliverables
│   └── task_dod_stop.py      # Block Stop if tasks incomplete
│
├── trackers/                 # PostToolUse recording
│   ├── phase_tracker.py      # Record phase changes
│   ├── deliverables_tracker.py # Mark deliverables complete
│   └── release_plan_tracker.py # Validate & record release plan items + RT- tasks
│
├── handlers/                 # Hook entry points
│   ├── pre_tool.py           # Routes PreToolUse to guards
│   ├── post_tool.py          # Routes PostToolUse to trackers
│   ├── user_prompt.py        # Handles UserPromptSubmit + validation detection
│   └── subagent_stop.py      # Handles SubagentStop
│
├── context/                  # Context injection
│   ├── context_injector.py   # Inject reminders + validation context
│   └── phase_reminders.py    # Phase-specific reminder content
│
├── validators/               # Criteria validation enforcement
│   ├── __init__.py
│   ├── criteria_validator.py # Detect pending AC/SC/epic SC validation
│   └── revision_manager.py   # Create and track revision tasks
│
├── release_plan/             # Release plan integration
│   ├── utils.py              # Find items (task, AC, SC, epic SC, etc.)
│   ├── getters.py            # Get current items from state
│   ├── checkers.py           # Check completion status (includes task-only checkers)
│   ├── resolvers.py          # Record completed items
│   ├── new_setters.py        # Update state values
│   ├── project.py            # Project directory types (FeatureSubdir)
│   └── state.py              # Project state file operations
│
├── logs/                     # Audit logs (auto-created)
│   └── violations.log        # Invariant violations and guard decisions
│
└── tests/
    ├── test_workflow_architecture.py
    ├── test_release_plan_tracker.py
    ├── test_phase_reminders.py
    ├── test_criteria_validator.py
    ├── test_revision_manager.py
    ├── test_task_dod_stop.py
    ├── test_troubleshoot_phase.py
    └── test_validation_integration.py
```

## Hook Event Flow

**1. UserPromptSubmit**

Triggered when user submits a prompt. Used for:
- Workflow activation via `/implement` command
- Workflow deactivation via `/deactivate-workflow`
- Troubleshoot mode via `/troubleshoot` command (bypasses coding phases)
- Pending validation detection (sets `pending_validation` flag in state)

**2. PreToolUse (Validation Phase)**

Triggered before any tool executes. **Blocks invalid operations.**

- Check workflow active; if inactive: `exit(0)` allow
- Route by `tool_name`:
  - **Skill tool**: `PhaseTransitionGuard` (phase order) + `ReleasePlanTracker.run_pre_tool` (validate IDs including `RT-` prefixed revision tasks)
  - **Task tool**: `SubagentAccessGuard` (subagent permissions)
- All checks pass: `exit(0)`. Any check fails: `exit(2)` + stderr

**3. PostToolUse (Recording Phase)**

Triggered after tool executes successfully. **Records state changes.**

- Check workflow active; if inactive: return
- Route by `tool_name`:
  - **Skill tool**: `PhaseTracker` + `ContextInjector` (phase reminders or validation context) + `DeliverableTracker` + `ReleasePlanTracker.run_post_tool`
  - **Write/Edit/Read/Bash**: `DeliverableTracker`
- After recording, the tracker checks if validation is needed:
  - Task completed -> check if AC validation needed
  - AC met -> check if SC validation needed
  - SC met -> check if epic SC validation needed

**4. Stop (Task DoD Enforcement)**

Triggered when the agent attempts to stop. **Blocks stop if tasks incomplete.**

- `TaskDodStopGuard` checks all `current_tasks` in project state
- If any task status != `"completed"` -> block with incomplete task IDs
- Also enforces completion of `RT-` prefixed revision tasks

## Criteria Validation System

When all tasks in a unit complete, the system auto-detects that criteria validation is needed and routes to the `validator` subagent.

**Validation chain:**
1. All tasks in user story completed -> **AC validation** pending
2. All user stories in feature completed -> **SC validation** pending
3. All features in epic completed -> **Epic SC validation** pending

**Detection flow:**
- `ReleasePlanTracker` sets `needs_ac_validation`, `needs_sc_validation`, or `needs_epic_sc_validation` flags in workflow state after recording completions
- On next `/implement`, `UserPromptHandler` reads these flags and sets `pending_validation`
- `ContextInjector` detects `pending_validation` and injects context instructing deployment of the `validator` subagent

**Validator subagent workflow:**
1. Read project state to identify pending validation type
2. Read release plan for criteria descriptions
3. Evaluate each criterion against the codebase
4. Invoke `/log:ac AC-XXX met|unmet` or `/log:sc SC-XXX met|unmet`
5. If any unmet: create revision tasks via `revision_manager`

**Revision tasks:**
- Created when criteria fail validation
- ID format: `RT-{round}-{number}` (e.g., `RT-1-001`, `RT-2-003`)
- Saved to `project/{version}/{epic_id}/{feature_id}/revisions/revision_tasks.json`
- Injected into `current_tasks` in project state
- Validated and tracked like regular tasks by `ReleasePlanTracker`

## Bypass Phases (Troubleshoot Mode)

Some phases can bypass normal phase ordering. The `troubleshoot` phase allows entering troubleshoot mode from any coding phase.

**Bypass Configuration** (`workflow.config.yaml`):
```yaml
bypass_phases:
  troubleshoot:
    can_bypass:      # Coding phases (can enter troubleshoot from these)
      - write-tests
      - review-tests
      - write-code
      - code-review
      - refactor
      - validate
      - commit
    cannot_bypass:   # Pre-coding phases (protected, cannot skip)
      - explore
      - plan
      - plan-consult
      - finalize-plan
```

**Troubleshoot Flow:**
1. User invokes `/troubleshoot` from a coding phase (e.g., `write-code`)
2. Current phase is stored in `pre_troubleshoot_phase`
3. Phase transitions to `troubleshoot`, owned by `troubleshooter` agent
4. User invokes `/troubleshoot` again to exit
5. Phase returns to stored `pre_troubleshoot_phase`

**State Changes:**
- `activate_troubleshoot()` - Stores current phase, sets `troubleshoot: true`
- `deactivate_troubleshoot()` - Restores previous phase, clears flag
- `is_troubleshoot_active()` - Check if in troubleshoot mode
- `get_pre_troubleshoot_phase()` - Get phase before troubleshoot

## Release Plan Integration

The `release_plan_tracker` validates and records release plan items:

**Validation (PreToolUse):**
1. Parse arguments -> `task_id`, `status`
2. For `RT-` prefixed IDs: validate against `current_tasks` in project state
3. For regular IDs: call `find_task()` / `find_acceptance_criteria()` / `find_success_criteria()`
4. If not found -> block. If found -> allow

**Recording (PostToolUse):**
1. `log:task` + `completed` -> `record_completed_task()` + check AC validation
2. `log:ac` + `met` -> `record_met_ac()` + check SC validation
3. `log:sc` + `met` -> `record_met_sc()` + check epic SC validation

**Supported commands:**
- `/log:task TXXX status` - statuses: `not_started`, `in_progress`, `completed`, `blocked`
- `/log:task RT-N-XXX status` - same statuses, for revision tasks
- `/log:ac AC-XXX status` - statuses: `met`, `unmet`
- `/log:sc SC-XXX status` - statuses: `met`, `unmet`

## State Management

**Workflow State** (`state.json`):

```json
{
  "workflow_active": true,
  "current_phase": "plan",
  "pending_validation": "ac",
  "needs_ac_validation": true,
  "deliverables": [...],
  "phase_history": ["explore"],
  "dry_run_active": false,
  "troubleshoot": false,
  "pre_troubleshoot_phase": null
}
```

**Project State** (`project/state.json`):

```json
{
  "current_epic_id": "E001",
  "current_feature_id": "F001",
  "current_user_story": "US-001",
  "current_tasks": {"T001": "completed", "RT-1-001": "not_started"},
  "current_acs": {"AC-001": "unmet"},
  "current_scs": {"SC-001": "unmet"},
  "completed_tasks": ["T000"],
  "completed_user_stories": [],
  "completed_features": [],
  "completed_epics": [],
  "met_acs": [],
  "met_scs": [],
  "met_epic_scs": []
}
```

## Key Design Decisions

1. **Separation of Concerns**: Guards validate, trackers record, validators enforce criteria, handlers route
2. **Exit Codes**: `0` = allow, `2` = block with error message
3. **Strict Order**: `strict_order` field actively blocks tool calls until lower-level deliverables are complete
4. **Singleton Patterns**: StateManager and PhaseEngine use module-level singletons
5. **Backward Compatibility**: Legacy functions wrap new classes for smooth migration
6. **Release Plan Integration**: Real validation against release plan, not just regex patterns
7. **Validation Chain**: AC -> SC -> Epic SC validation triggered automatically on completion
8. **Revision Tasks**: Failed criteria generate `RT-` prefixed tasks that integrate with existing task tracking
9. **Audit System**: Non-blocking invariant checks with violation logging for post-hoc analysis
10. **Bypass Phases**: Special phases (e.g., `troubleshoot`) can skip normal ordering from coding phases while protecting pre-coding phases

## Audit System

The `WorkflowAuditor` detects guard failures and state corruption without breaking workflow execution. All write errors are silently caught.

**Invariant Checks:**
- `check_strict_order_compliance` - Verify completed deliverables respect `strict_order`
- `check_phase_validity` - Verify phase exists in config
- `check_empty_deliverables` - Warn on zero deliverables for a phase
- `check_state_integrity` - Verify required keys exist with correct types
- `check_state_corruption` - Detect JSON corruption on state load
- `check_phase_deliverable_match` - Verify deliverable count matches config

**Log Format:**
```
[2025-01-15 10:30:45] [VIOLATION] [STRICT_ORDER] Level 2 deliverable complete while level 1 still pending
[2025-01-15 10:30:46] [DECISION] [PhaseTransitionGuard] ALLOW explore -> plan
[2025-01-15 10:30:47] [WARN] [EMPTY_DELIVERABLES] Phase 'custom' has 0 deliverables
```

**Log Location:** `logs/violations.log` (auto-rotates at 5MB)

**Usage:**
```python
from core.workflow_auditor import get_auditor

auditor = get_auditor()
auditor.check_state_integrity(state)
auditor.log_decision("MyGuard", "BLOCK", "reason: invalid phase")
```

## Testing

Run all tests (511 tests):
```bash
python -m pytest .claude/hooks/workflow/tests/ -v
```

Run specific test file:
```bash
python -m pytest .claude/hooks/workflow/tests/test_criteria_validator.py -v
python -m pytest .claude/hooks/workflow/tests/test_troubleshoot_phase.py -v
```

## Adding New Guards/Trackers

**New Guard (PreToolUse or Stop):**

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

2. Import and use in `handlers/pre_tool.py` or register in `hooks-registry.json`

**New Tracker (PostToolUse):**

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

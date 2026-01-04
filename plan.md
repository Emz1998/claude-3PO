# Dynamic Implement Workflow

## Overview

Milestone-scoped, dependency-driven workflow for `/implement` command.

**Core Principles:**

- Engineers triggered based on `task.owner` field from roadmap
- Parallel execution for tasks with all dependencies completed (within same milestone)
- Sequential planning phase: codebase-explorer → planner → consultant
- **Main agent** handles all roadmap logging via `/log:roadmap` after code-reviewer confirms ACs passed
- Stop blocked until milestone fully complete (tasks, ACs, SCs)

**Workflow Flow:**

1. `/implement [MS-XXX]` triggered → targets specified milestone or `roadmap.current.milestone` if no args
2. Read todo file: `project/{version}/{phase}/{milestone}/todo_{yyyy-mm-dd}_{session_id}.md`
3. Planning phase (sequential): codebase-explorer → planner → consultant
4. Coding phase (parallel): spawn engineers for ready tasks grouped by owner
5. After ALL engineers in batch complete → spawn ONE code-reviewer for all tasks
6. Code-reviewer writes to `project/{v}/{p}/{m}/code-review_{date}_{session}.md`
7. Code-reviewer evaluates all tasks and reports:
   - Tasks with ACs passed → ready for logging
   - Tasks needing revision → recall task owner (optional iteration)
8. If revision needed → spawn task owner engineer → code-reviewer re-reviews
9. Main agent uses `/log:roadmap` for each task with passed ACs
10. Check for newly ready tasks → spawn more engineers if any
11. Loop until all tasks in milestone complete
12. All tasks done → main agent logs SCs via `/log:roadmap`
13. Stop blocked until all tasks completed + all ACs met + all SCs met

**Workflow Diagram:**

```
                     /implement [MS-XXX]
                              |
                              v
                 +------------------------+
                 |  args? → use MS-XXX    |
                 |  no args? → use        |
                 |  roadmap.current       |
                 +------------------------+
                              |
                              v
                 +------------------------+
                 |  Read todo file:       |
                 |  project/{v}/{p}/{m}/  |
                 |  todo_{date}_{sid}.md  |
                 +------------------------+
                              |
                              v
     +------------------------------------------------+
     |              PLANNING PHASE (Sequential)       |
     |                                                |
     |  codebase-explorer -----> planner              |
     |        |                     |                 |
     |        v                     v                 |
     |  [codebase-status.md]   [plan.md]              |
     |                              |                 |
     |                              v                 |
     |                        consultant              |
     |                              |                 |
     |                              v                 |
     |                    [revise plan.md]            |
     +------------------------------------------------+
                              |
                              v
     +------------------------------------------------+
     |              CODING PHASE (Parallel)           |
     |                                                |
     |  Query ready tasks in milestone (deps met)     |
     |                      |                         |
     |                      v                         |
     |  Group by owner: {backend: [T007, T008],       |
     |                   fullstack: [T004, T005]}     |
     |                      |                         |
     |         +------------+------------+            |
     |         |            |            |            |
     |         v            v            v            |
     |   +---------+  +---------+  +---------+        |
     |   | backend |  | backend |  |fullstack|        |
     |   |  T007   |  |  T008   |  |  T004   |  ...   |
     |   +---------+  +---------+  +---------+        |
     |         |            |            |            |
     |         v            v            v            |
     |      [work]       [work]       [work]          |
     |         |            |            |            |
     |         +------------+------------+            |
     |                      |                         |
     |                      v                         |
     |            +-------------------+               |
     |            |   code-reviewer   |               |
     |            | (all tasks batch) |               |
     |            +-------------------+               |
     |                      |                         |
     |                      v                         |
     |            [AC check per task]                 |
     |                      |                         |
     |                      v                         |
     |         /log:roadmap for each task             |
     |         with passed ACs                        |
     |                      |                         |
     |                      |                         |
     |                      v                         |
     |          Check newly ready tasks               |
     |                      |                         |
     |         +------------+------------+            |
     |         |                         |            |
     |    [more ready]              [none ready]      |
     |         |                         |            |
     |         v                         v            |
     |    Loop back              All tasks done?      |
     |                                   |            |
     |                      +------------+            |
     |                      |                         |
     |                      v                         |
     |    Main agent /log:roadmap (SCs)               |
     +------------------------------------------------+
                              |
                              v
     +------------------------------------------------+
     |                 STOP GUARD                     |
     |                                                |
     |  Tasks complete? --[NO]--> Block               |
     |         |                                      |
     |        [YES]                                   |
     |         v                                      |
     |  ACs met? --------[NO]--> Block                |
     |         |                                      |
     |        [YES]                                   |
     |         v                                      |
     |  SCs met? --------[NO]--> Block                |
     |         |                                      |
     |        [YES]                                   |
     |         v                                      |
     |      ALLOW STOP --> Workflow ends              |
     +------------------------------------------------+
```

## File Changes

**`workflow/implement_state.py`** - Simplify

_Cache structure:_

- `implement_workflow_active`: bool
- `implement_phase`: "planning" | "coding"
- `planning_step`: "codebase-explorer" | "planner" | "consultant" | "done"
- `target_milestone`: milestone ID from `roadmap.current.milestone`

_Functions:_

- `activate_workflow()` - Initialize with target milestone
- `deactivate_workflow()` - Clear cache
- `is_workflow_active()` - Check if active
- `get_implement_phase()` - Get current phase
- `get_planning_step()` - Get planning step
- `get_target_milestone()` - Get target milestone ID
- `set_implement_phase(phase)` - Set phase
- `advance_planning_step()` - Advance to next planning step

**`roadmap/utils.py`** - Extend

_New functions:_

- `get_ready_tasks_in_milestone(roadmap, milestone_id)` - Get tasks where status=not_started and deps completed
- `group_tasks_by_owner(tasks)` - Group task list by owner field
- `is_milestone_complete(roadmap, milestone_id)` - Returns (bool, reason) checking tasks/ACs/SCs

**`guardrails/implement_workflow_guard.py`** - Rewrite

_PreToolUse guard for Task tool:_

- Planning phase: enforce sequential order (codebase-explorer → planner → consultant)
- Coding phase: validate engineer matches ready task owner in target milestone
- Allow ONE code-reviewer after ALL engineers in batch complete
- Block with informative message if wrong subagent

**`guardrails/planning_write_guard.py`** - Create

_PreToolUse guard for Write/Edit tools during planning phase:_

- **codebase-explorer**: only Write to `project/{v}/{p}/{m}/codebase-status_{date}_{session}.md`
- **planner**: only Write to `project/{v}/{p}/{m}/plan_{date}_{session}.md`
- **consultant**: only Edit/Write to `project/{v}/{p}/{m}/plan_{date}_{session}.md`
  - Must add front matter: `revised_by: consultant-agent`
- Block writes to any other paths with informative message

**`guardrails/test_engineer_write_guard.py`** - Create

_PreToolUse guard for Write/Edit tools for test-engineer:_

- Only allow writes to test files matching patterns:
  - `*.test.{ts,tsx,js,jsx}` (JS/TS test files)
  - `*.spec.{ts,tsx,js,jsx}` (JS/TS spec files)
  - `test_*.py` or `*_test.py` (Python test files)
  - Files in `__tests__/` or `tests/` directories
- Block writes to non-test files with: "test-engineer can only write to test files"

**`guardrails/milestone_completion_guard.py`** - Create

_Stop hook guard:_

- Check if workflow active
- Call `is_milestone_complete()` for target milestone
- Block stop if incomplete with reason:
  - "Incomplete tasks: T004, T005"
  - "Task T004 has unmet ACs: AC-004, AC-005"
  - "Unmet success criteria: SC-002"

**`workflow/implement_progress.py`** - Simplify

_PostToolUse tracker for Task tool:_

- Planning phase: advance step, inject ready tasks context when done
- Coding phase: after code-reviewer completes, inject context for main agent to log via `/log:roadmap`

**`workflow/implement_detector.py`** - Update

_UserPromptSubmit hook:_

- Detect `/implement [MS-XXX]` or `/build [MS-XXX]` command
- If args provided → use specified milestone ID
- If no args → use `roadmap.current.milestone`
- Call `activate_workflow(milestone_id)`

**`.claude/commands/log/log:roadmap.md`** - Create

_Skill for logging roadmap status:_

- Usage: `/log:roadmap <task_id>` or `/log:roadmap --sc <sc_id>`
- For tasks: auto-resolve task status + associated ACs from roadmap
- For SCs: mark success criteria as met
- Calls underlying `roadmap_status.py` script

## Hook Registration

**PreToolUse:**

- Matcher: `Task` → `implement_workflow_guard.py`
- Matcher: `Write|Edit` → `planning_write_guard.py` (planning phase)
- Matcher: `Write|Edit` → `test_engineer_write_guard.py` (test-engineer)

**PostToolUse:**

- Matcher: `Task` → `implement_progress.py`

**Stop:**

- Command: `milestone_completion_guard.py`

**UserPromptSubmit:**

- Command: `implement_detector.py`

## Guard Logic

**Planning Phase (Task spawn):**

```
if subagent != expected_planning_step:
    block("Planning phase: expected {expected}, not {subagent}")
```

**Planning Write Guard:**

```
base_path = "project/{version}/{phase}/{milestone}/"

if subagent == "codebase-explorer":
    allowed = base_path + "codebase-status_{date}_{session}.md"
elif subagent == "planner":
    allowed = base_path + "plan_{date}_{session}.md"
elif subagent == "consultant":
    allowed = base_path + "plan_{date}_{session}.md"
    # Must include: revised_by: consultant-agent in front matter

if file_path != allowed:
    block("{subagent} can only write to {allowed}")
```

**Test Engineer Write Guard:**

```
TEST_PATTERNS = [
    r".*\.test\.(ts|tsx|js|jsx)$",
    r".*\.spec\.(ts|tsx|js|jsx)$",
    r".*/test_.*\.py$",
    r".*_test\.py$",
    r".*/__tests__/.*",
    r".*/tests/.*",
]

if subagent == "test-engineer":
    if not matches_any(file_path, TEST_PATTERNS):
        block("test-engineer can only write to test files")
```

**Coding Phase:**

```
ready_tasks = get_ready_tasks_in_milestone(milestone_id)
ready_by_owner = group_tasks_by_owner(ready_tasks)

if engineer not in ready_by_owner:
    block("No ready tasks for {engineer}. Ready owners: {owners}")

# code-reviewer allowed after engineers complete work (per task)
```

**Stop Guard:**

```
complete, reason = is_milestone_complete(milestone_id)
if not complete:
    block("Cannot stop: {reason}")
```

## Example Flow (MS-002)

**Milestone MS-002** - Data Models and TypeScript Interfaces:

- T004: Create Prediction interface (owner: fullstack-developer, deps: [])
- T005: Create User/Subscription interfaces (owner: fullstack-developer, deps: [])
- T006: Create NBA Team/Game interfaces (owner: fullstack-developer, deps: [])

**Execution:**

1. `/implement MS-002` (or `/implement` if MS-002 is current)
2. Read todo file for context: `project/v0.1.0/phase-1/MS-002/todo_{date}_{session}.md`
3. codebase-explorer writes codebase-status.md → planner writes plan.md → consultant revises plan.md
4. Context injected: "Ready tasks: fullstack-developer: [T004, T005, T006]"
5. Main agent spawns 3 fullstack-developer subagents in parallel
6. Each engineer works on assigned task
7. T004 engineer completes → main agent spawns code-reviewer for T004
8. T004 code-reviewer reports: "ACs passed"
9. Main agent uses `/log:roadmap T004` → marks T004 completed + ACs met
10. (Same flow for T005, T006 in parallel)
11. After each task logged → check for newly ready tasks → loop if any
12. All tasks done → main agent logs SCs via `/log:roadmap`
13. User tries to stop → guard checks completion
14. All complete → stop allowed → workflow ends

## Files Summary

**Modify:**

- `workflow/implement_state.py` - Simplified cache structure
- `roadmap/utils.py` - Add milestone queries
- `guardrails/implement_workflow_guard.py` - Phase validation
- `workflow/implement_progress.py` - Inject context for main agent logging
- `workflow/implement_detector.py` - Target milestone init

**Create:**

- `guardrails/milestone_completion_guard.py` - Stop guard
- `guardrails/planning_write_guard.py` - Write/Edit guard for planning subagents
- `guardrails/test_engineer_write_guard.py` - Write/Edit guard for test-engineer
- `.claude/commands/log/log:roadmap.md` - Skill to log task/AC/SC status

**Update:**

- `hooks-registry.json` - Add Stop hook
- `.claude/settings.local.json` - Register hooks

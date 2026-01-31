# Workflow Architecture

## Overview

The workflow system enforces a structured development process through Claude Code hooks. It integrates two data sources:

- **roadmap.json** - Source of truth for WHAT to build (tasks, ACs, milestones)
- **workflow.yaml** - Source of truth for HOW to build (phases, subphases, agents)

---

## System Architecture

```
                              CLAUDE CODE SESSION
  +-------------+    +-------------+    +-------------+    +-------------+
  | Main Agent  |--->|  Subagent   |--->|  Subagent   |--->|  Subagent   |
  |             |    |  (Task)     |    |  (Task)     |    |  (Task)     |
  +------+------+    +------+------+    +------+------+    +------+------+
         |                  |                  |                  |
         v                  v                  v                  v
  +-----------------------------------------------------------------------+
  |                            HOOKS LAYER                                 |
  |                                                                        |
  |  +------------------+  +------------------+  +----------------------+  |
  |  | pre_tool_use.py  |  | post_tool_use.py |  | stop/subagent_stop   |  |
  |  |                  |  |                  |  |                      |  |
  |  | - Block wrong    |  | - Track tools    |  | - Check milestone    |  |
  |  |   subagent       |  | - Record ACs     |  |   completed (main)   |  |
  |  | - Enforce phase  |  | - Auto-resolve   |  | - Check task         |  |
  |  |   ownership      |  |   statuses       |  |   completed (sub)    |  |
  |  +--------+---------+  +--------+---------+  +-----------+----------+  |
  |           |                     |                        |             |
  +-----------+---------------------+------------------------+-------------+
              |                     |                        |
              +---------------------+------------------------+
                                    |
                                    v
  +-----------------------------------------------------------------------+
  |                          LIBRARY LAYER                                 |
  |                                                                        |
  |  +---------------------------+    +--------------------------------+  |
  |  |     workflow/lib/         |    |         roadmap/               |  |
  |  |                           |    |                                |  |
  |  | - state.py                |    | - utils.py                     |  |
  |  |   - phase transitions     |    |   - get_task()                 |  |
  |  |   - workflow state        |    |   - get_milestone()            |  |
  |  |                           |    |   - is_task_completed()        |  |
  |  | - guardrails.py           |<---|   - is_milestone_completed()   |  |
  |  |   - check_subagent        |    |   - are_all_acs_met_in_task()  |  |
  |  |   - check_can_stop        |    |                                |  |
  |  |     (reads roadmap)       |    | - resolver.py                  |  |
  |  |                           |    |   - auto-resolve statuses      |  |
  |  +---------------------------+    +--------------------------------+  |
  |                                                                        |
  +-----------------------------------+------------------------------------+
                                      |
                                      v
  +-----------------------------------------------------------------------+
  |                        PERSISTENCE LAYER                               |
  |                                                                        |
  |  +---------------------------+    +--------------------------------+  |
  |  | workflow/state/           |    | project/{version}/release-plan/|  |
  |  | workflow.json             |    | roadmap.json                   |  |
  |  |                           |    |                                |  |
  |  | - workflow_active         |    | - current: {phase, milestone,  |  |
  |  | - current_phase           |    |             task}              |  |
  |  | - current_subphase        |    | - phases[]                     |  |
  |  | - development_mode        |    |   - milestones[]               |  |
  |  | - deliverables_met        |    |     - tasks[]                  |  |
  |  |                           |    |       - acceptance_criteria[]  |  |
  |  | (Process State)           |    |                                |  |
  |  +---------------------------+    | (Source of Truth)              |  |
  |                                   +--------------------------------+  |
  |  +---------------------------+                                        |
  |  | workflow/config/          |                                        |
  |  | workflow.yaml             |                                        |
  |  |                           |                                        |
  |  | - phases[]                |                                        |
  |  | - coding_phases_order     |                                        |
  |  | - stop_conditions         |                                        |
  |  |                           |                                        |
  |  | (Phase Rules)             |                                        |
  |  +---------------------------+                                        |
  |                                                                        |
  +-----------------------------------------------------------------------+
```

---

## Data Hierarchy

```
roadmap.json
|
+-- current: { phase, milestone, task }     <-- Active work pointer
|
+-- phases[]
    |
    +-- id: "PH-001"
    +-- status: not_started | in_progress | completed
    |
    +-- milestones[]
        |
        +-- id: "MS-001"
        +-- status: not_started | in_progress | completed
        +-- test_strategy: "TDD" | "TA"     <-- Determines subphase order
        |
        +-- success_criteria[]              <-- Required for milestone completion
        |   +-- id: "SC-001"
        |   +-- status: met | unmet
        |
        +-- tasks[]
            |
            +-- id: "T001"
            +-- owner: "frontend-engineer"  <-- Determines subagent
            +-- status: not_started | in_progress | completed
            |
            +-- acceptance_criteria[]       <-- Required for task completion
                +-- id: "AC-001"
                +-- status: met | unmet
```

---

## Stop Conditions

### Completion Hierarchy (Bottom-Up)

```
+------------------------------------------------------------------+
|                     COMPLETION RULES                              |
|                                                                   |
|   LEVEL 1: Acceptance Criteria (AC)                               |
|   +----------------------------------------------------------+   |
|   | AC is marked "met" via /log:ac skill                      |   |
|   +----------------------------------------------------------+   |
|                              |                                    |
|                              v                                    |
|   LEVEL 2: Task                                                   |
|   +----------------------------------------------------------+   |
|   | Task is "completed" when:                                 |   |
|   |   ALL acceptance_criteria[].status == "met"               |   |
|   +----------------------------------------------------------+   |
|                              |                                    |
|                              v                                    |
|   LEVEL 3: Milestone                                              |
|   +----------------------------------------------------------+   |
|   | Milestone is "completed" when:                            |   |
|   |   ALL tasks[].status == "completed"                       |   |
|   |   AND                                                     |   |
|   |   ALL success_criteria[].status == "met"                  |   |
|   +----------------------------------------------------------+   |
|                              |                                    |
|                              v                                    |
|   LEVEL 4: Phase                                                  |
|   +----------------------------------------------------------+   |
|   | Phase is "completed" when:                                |   |
|   |   ALL milestones[].status == "completed"                  |   |
|   +----------------------------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

### Stop Condition Rules

| Agent Type     | Can Stop When                                        | Check Function             |
| -------------- | ---------------------------------------------------- | -------------------------- |
| **Subagent**   | Current task is completed (all ACs met)              | `is_task_completed()`      |
| **Main Agent** | Current milestone is completed (all tasks + SCs met) | `is_milestone_completed()` |

### Stop Validation Flow

```
                     Agent tries to stop
                            |
                            v
              +---------------------------+
              |  Is workflow_active?      |
              +-------------+-------------+
                            | yes
                            v
              +---------------------------+
              |  Load roadmap.json        |
              |  Get current milestone    |
              +-------------+-------------+
                            |
          +-----------------+-----------------+
          |                                   |
          v                                   v
  +---------------+                   +---------------+
  |  MAIN AGENT   |                   |   SUBAGENT    |
  |               |                   |               |
  |  Check:       |                   |  Check:       |
  |  is_milestone |                   |  is_task      |
  |  _completed() |                   |  _completed() |
  |               |                   |               |
  |  Requires:    |                   |  Requires:    |
  |  - All tasks  |                   |  - All ACs    |
  |    completed  |                   |    met        |
  |  - All SCs    |                   |               |
  |    met        |                   |               |
  +-------+-------+                   +-------+-------+
          |                                   |
          v                                   v
  +-----------------------------------------------+
  |                                               |
  |   ALLOW STOP          or        BLOCK STOP   |
  |   (conditions met)              (with reason)|
  |                                               |
  +-----------------------------------------------+
```

---

## Workflow Phases

### Main Phases (Sequential)

```
explore --> plan --> plan-consult --> code --> commit
```

| Phase          | Agent Owner         | Purpose                                  |
| -------------- | ------------------- | ---------------------------------------- |
| `explore`      | codebase-explorer   | Analyze codebase, generate status report |
| `plan`         | planning-specialist | Create implementation plan               |
| `plan-consult` | plan-consultant     | Review and validate plan                 |
| `code`         | (subphases)         | Implementation work                      |
| `commit`       | version-manager     | Commit changes to git                    |

### Code Phase Subphases

The `code` phase has subphases ordered by `milestone.test_strategy`:

**TDD Mode:**

```
write_test --> review_test --> implement --> review_code --> refactor --> validate
```

**Test-After Mode:**

```
implement --> review_code --> write_test --> review_test --> refactor --> validate
```

| Subphase      | Agent Owner   |
| ------------- | ------------- |
| `write_test`  | test-engineer |
| `review_test` | test-reviewer |
| `implement`   | main-agent    |
| `review_code` | code-reviewer |
| `refactor`    | main-agent    |
| `validate`    | validator     |

---

## Phase Transition Enforcement

### Rules

1. **Sequential Order**: Phases must complete in order (no skipping)
2. **No Backwards**: Cannot return to completed phases
3. **Prerequisites**: Some phases require prior phases in history

```
+-------------------------------------------------------------------+
|                    PHASE TRANSITION VALIDATION                     |
|                                                                    |
|   Current: "explore"                                               |
|   History: []                                                      |
|                                                                    |
|   +---------------------+------------------+--------------------+  |
|   |  Transition To      |  Allowed?        |  Reason            |  |
|   +---------------------+------------------+--------------------+  |
|   |  explore            |  YES (complete)  |                    |  |
|   |  plan               |  YES             |  explore in history|  |
|   |  plan-consult       |  NO              |  requires plan     |  |
|   |  code               |  NO              |  skip plan, p-c    |  |
|   +---------------------+------------------+--------------------+  |
|                                                                    |
+-------------------------------------------------------------------+
```

### Validation in state.py

```python
def validate_phase_transition(self, new_phase: str) -> Tuple[bool, str]:
    # 1. Check phase exists
    # 2. Check requires_phase is in phase_history
    # 3. Check sequential order (no skip, no backwards)
    ...
```

---

## Agent Ownership Resolution

### Priority Order

1. **Subphase owner** (in code phase) - from workflow.yaml
2. **Task owner** - from roadmap.json
3. **Phase owner** - from workflow.yaml

```
+-------------------------------------------------------------------+
|                    OWNERSHIP RESOLUTION                            |
|                                                                    |
|   roadmap.json                    workflow.yaml                    |
|   +-------------------+           +------------------------+       |
|   | task: {           |           | phases:                |       |
|   |   owner:          |           |   - name: code         |       |
|   |   "frontend-eng"  |           |     subphases: ...     |       |
|   | }                 |           |                        |       |
|   +-------------------+           |   - name: write_test   |       |
|           |                       |     agent_owner:       |       |
|           |                       |     "test-engineer"    |       |
|           |                       +------------------------+       |
|           |                                  |                     |
|           v                                  v                     |
|   +---------------------------------------------------+           |
|   |              RESOLUTION LOGIC                      |           |
|   |                                                    |           |
|   |  if current_phase == "code" AND current_subphase:  |           |
|   |      return subphase.agent_owner                   |           |
|   |  elif task.owner:                                  |           |
|   |      return task.owner                             |           |
|   |  else:                                             |           |
|   |      return phase.agent_owner                      |           |
|   +---------------------------------------------------+           |
|                                                                    |
+-------------------------------------------------------------------+
```

---

## Hook Enforcement Matrix

| Action                          | pre_tool_use   | post_tool_use | stop             |
| ------------------------------- | -------------- | ------------- | ---------------- |
| Call wrong subagent             | BLOCK          | -             | -                |
| Skip phase                      | (via state.py) | -             | -                |
| Go backwards                    | (via state.py) | -             | -                |
| Write file                      | -              | RECORD        | -                |
| Mark AC met                     | -              | RECORD        | -                |
| Stop without task complete      | -              | -             | BLOCK (subagent) |
| Stop without milestone complete | -              | -             | BLOCK (main)     |

---

## Auto-Resolution Flow (resolver.py)

```
+-------------------------------------------------------------------+
|                    AUTO-RESOLUTION                                 |
|                                                                    |
|   When AC is marked "met" via /log:ac:                             |
|                                                                    |
|   +------------------+                                             |
|   | AC marked "met"  |                                             |
|   +--------+---------+                                             |
|            |                                                       |
|            v                                                       |
|   +--------------------------------------------------+            |
|   | _resolve_task(task)                              |            |
|   |                                                  |            |
|   | if all(ac.status == "met"):                      |            |
|   |     task.status = "completed"                    |            |
|   +--------+-----------------------------------------+            |
|            | task completed                                        |
|            v                                                       |
|   +--------------------------------------------------+            |
|   | _resolve_milestone(milestone)                    |            |
|   |                                                  |            |
|   | if all(task.status == "completed")               |            |
|   |    AND all(sc.status == "met"):                  |            |
|   |     milestone.status = "completed"               |            |
|   +--------+-----------------------------------------+            |
|            | milestone completed                                   |
|            v                                                       |
|   +--------------------------------------------------+            |
|   | _resolve_phase(phase)                            |            |
|   |                                                  |            |
|   | if all(milestone.status == "completed"):         |            |
|   |     phase.status = "completed"                   |            |
|   +--------+-----------------------------------------+            |
|            |                                                       |
|            v                                                       |
|   +--------------------------------------------------+            |
|   | _resolve_current(phases)                         |            |
|   |                                                  |            |
|   | Advance roadmap.current to next incomplete:      |            |
|   | - current.task                                   |            |
|   | - current.milestone                              |            |
|   | - current.phase                                  |            |
|   +--------------------------------------------------+            |
|                                                                    |
+-------------------------------------------------------------------+
```

---

## File Reference

| File                                          | Purpose                                            |
| --------------------------------------------- | -------------------------------------------------- |
| `.claude/hooks/workflow/pre_tool_use.py`      | Block wrong subagents before tool execution        |
| `.claude/hooks/workflow/post_tool_use.py`     | Track tool usage, record deliverables              |
| `.claude/hooks/workflow/stop.py`              | Validate main agent can stop (milestone complete)  |
| `.claude/hooks/workflow/subagent_stop.py`     | Validate subagent can stop (task complete)         |
| `.claude/hooks/workflow/lib/state.py`         | Workflow state management, phase transitions       |
| `.claude/hooks/workflow/lib/guardrails.py`    | Validation functions, config loading               |
| `.claude/hooks/workflow/config/workflow.yaml` | Phase definitions, subphase order, stop conditions |
| `.claude/hooks/workflow/state/workflow.json`  | Runtime workflow state                             |
| `.claude/hooks/roadmap/utils.py`              | Roadmap getters, status checkers                   |
| `.claude/hooks/roadmap/resolver.py`           | Auto-resolve statuses bottom-up                    |
| `project/{version}/release-plan/roadmap.json` | Source of truth for tasks and completion           |

# Workflow Hooks Architecture

## Overview

A state-machine enforcement layer built on Claude Code's hooks API. It intercepts hook events (PreToolUse, PostToolUse, UserPromptSubmit, Stop) to enforce ordered phases, agent sequencing, validation loops, and contextual reminders across parallel worktree sessions.

All hooks check `workflow_active` first and short-circuit when inactive. State is shared via a single file-locked `state.json` in the main worktree.

---

## Entry Point

`/build` is the single entry point. It detects what work is available and launches parallel sessions:

```
/build
  │
  ├─ Open PRs exist?
  │    ├─ Yes → launch /review <pr_number> per PR   (PR-Review Workflow)
  │    └─ No  → launch /implement <story_id> per Ready story  (Implement Workflow)
  │
  └─ Each session → own tmux session + git worktree
```

**Routing**: `build_entry.py` (UserPromptSubmit) checks for open PRs via `pr_manager.py`. If found, routes to PR-Review. Otherwise, lists Ready stories via `project_manager.py` and routes to Implement.

---

## Implement Workflow

### Phases

```
pre-coding → code → review → final-commit → create-pr → validate → push → [CI check] → done
                      ↑           │
                      └─ refactor ◄┘  (review loop, max 3 iterations)
```

| Phase | Skill | Predecessor | What Happens |
|---|---|---|---|
| `pre-coding` | `/implement` (entry) | — | Explore → Plan → plan-reviewer |
| `code` | `/code` | `pre-coding` | test-engineer → test-reviewer |
| `review` | `/code-review` | `code` | code-reviewer → [review loop](#review-loop) |
| `final-commit` | `/commit` | `review` | Commit approved changes |
| `create-pr` | `/create-pr` | `final-commit` | Create pull request |
| `validate` | `/validate` | `create-pr` | Verify all requirements met |
| `push` | `/push` | `validate` | Push to remote → [CI check](#ci-check-loop) |

**Auto-triggers** (not phases):
- `/simplify` — fires on `PostToolUse[Write]` for new files only (any phase)
- `/refactor` — fires when review loop confidence < threshold

### Phase Enforcement

Each phase carries its own guard in skill frontmatter via shared `phase_guard.py`:

```
python3 phase_guard.py <expected_predecessor> <current_phase>
```

The guard:
1. Checks `workflow_active` — skips if inactive
2. Checks `session.control.hold` — blocks if on hold
3. Checks `session.control.blocked_until_phase` — blocks if gated
4. Validates `session.phase.previous == expected_predecessor`
5. If valid: records transition to state, exits 0. If invalid: exits 2 (block).

```yaml
# Example: .claude/commands/code.md
---
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' pre-coding code"
          timeout: 10
---
```

| Phase | Command File | Guard Args |
|---|---|---|
| `pre-coding` | — (set by `implement_trigger.py`) | No guard — entry point |
| `code` | `.claude/commands/code.md` | `pre-coding code` |
| `review` | `.claude/commands/code-review.md` | `code review` |
| `final-commit` | `.claude/commands/commit.md` | `review final-commit` |
| `create-pr` | `.claude/commands/create-pr.md` | `final-commit create-pr` |
| `validate` | `.claude/commands/validate.md` | `create-pr validate` |
| `push` | `.claude/commands/push.md` | `validate push` |

**Why frontmatter over centralized settings**: Each phase owns its guard — self-contained, scoped to that skill's lifecycle, no matcher regex needed.

### Entry: implement_trigger.py

Fires on `UserPromptSubmit` when prompt starts with `/implement`:

```
/implement <story_id>
  ├─ activate_workflow()
  ├─ Create session entry in state.json
  ├─ Create session context directory (.claude/sessions/SPRINT-NNN/STORY-ID/)
  ├─ Record phase = "pre-coding"
  ├─ Update story status → "In progress"
  └─ Output story context to Claude
```

### Stop Conditions

`stop_guard.py` (Stop event) blocks unless:
- `story.status == "Done"`
- `session.pr.created == true`
- `session.ci.status == "pass"`

On allow, writes `session.control.status = "completed"` to state.

---

## PR-Review Workflow

### Phases

```
pr-review → approve / request-changes → done
               ↑                    │
               └── fix + re-review ◄┘  (review loop, max 3 iterations)
```

| Phase | Description |
|---|---|
| `pr-review` | Reviewer reads PR diff, comments, context |
| `approve` | Scores meet threshold → `gh pr review --approve` |
| `request-changes` | Scores below threshold → post comments, wait for fixes, re-review |
| `done` | Session ends |

No phase guards — uses the [review loop](#review-loop) directly. CI checks are **not** handled; the reviewer only reports CI status.

### Entry: review_trigger.py

Fires on `UserPromptSubmit` when prompt starts with `/review`:

```
/review <pr_number>
  ├─ activate_workflow(type="pr-review")
  ├─ Create session entry in state.json (keyed as PR-<number>)
  └─ Output PR context to Claude
```

---

## Validation Loops

Both workflows share the same validation infrastructure. All three hooks live in the **code-reviewer agent frontmatter** as Stop hooks (auto-converted to SubagentStop):

```yaml
# .claude/agents/code-reviewer.md
---
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/decision_guard.py'"
          timeout: 10
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/validation_loop.py'"
          timeout: 10
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/escalate.py'"
          timeout: 10
---
```

### Review Loop

Runs when code-reviewer agent stops (SubagentStop). Prevents moving forward until review quality is satisfied.

```
code-reviewer stops
  │
  ├─ decision_guard.py: Was /decision invoked?
  │    └─ No → BLOCK: "Must invoke /decision <confidence> <quality>"
  │
  ├─ validation_loop.py: confidence >= 70 (threshold)?
  │    ├─ Yes → ALLOW (proceed to next phase)
  │    └─ No → iteration < 3 (max)?
  │         ├─ Yes → BLOCK: trigger /refactor, re-run reviewer
  │         │        (iteration_count++, decision_invoked reset)
  │         └─ No  → ESCALATE to user
  │
  └─ escalate.py: Sets escalate_to_user=true, surfaces message
```

| Config | Default | Location |
|---|---|---|
| confidence_threshold | 70 | `config.yaml → validation.confidence_score` |
| quality_threshold | 70 | `config.yaml → validation.quality_score` |
| max_iterations | 3 | `config.yaml → validation.iteration_loop` |

### CI Check Loop

Runs after `/push` completes (PostToolUse[Skill] on `/push`). Implement Workflow only.

```
ci_check_handler.py (after push)
  │
  ├─ Poll: gh pr checks <pr_number>
  │    ├─ pending → wait + re-poll
  │    ├─ pass → done (workflow complete)
  │    └─ fail → iteration < 2 (max)?
  │         ├─ Yes → /troubleshoot → fix → commit → push → re-poll
  │         └─ No  → ESCALATE to user
```

**Why max 2 (not 3)**: CI failures are often not auto-fixable (infra, secrets, flaky tests). Escalate early for human judgment.

| Config | Default | Location |
|---|---|---|
| ci_max_iterations | 2 | `config.yaml → validation.ci_max_iterations` |

---

## Session Orchestration

### Worktree Layout

Each session runs in an isolated git worktree created by `claude --worktree`:

```
/build → launch-claude.py (tmux orchestrator)
  │
  ├─ Load sprint ID from project_manager.py
  ├─ For each prompt:
  │    ├─ Extract story/PR ID via regex: (US|TS|SK|BG)-\d{3}
  │    ├─ Create tmux session named after story ID
  │    └─ Run: STORY_ID=SK-001 claude --worktree SPRINT-001/SK-001 "/implement SK-001"
  │
  └─ Claude Code creates worktree at: .claude/worktrees/SPRINT-001/SK-001/
```

```
.claude/worktrees/SPRINT-001/
├── SK-001/    ← /implement SK-001
├── SK-002/    ← /implement SK-002
└── SK-003/    ← /implement SK-003
```

### Tmux Sessions

Each story gets its own tmux session (not window), named after the story ID:

```
tmux sessions:
  SK-001 → claude --worktree SPRINT-001/SK-001 "/implement SK-001"
  SK-002 → claude --worktree SPRINT-001/SK-002 "/implement SK-002"
```

Switch between sessions: `tmux attach -t SK-001`

### Session Identity

| Mechanism | Purpose | Set By |
|---|---|---|
| `STORY_ID` env var | Primary — hooks use this to find their session in state.json | `launch-claude.py` |
| `session_id` field | Audit — Claude Code's session UUID for log correlation | `implement_trigger.py` |

```python
story_id = os.environ["STORY_ID"]
session = state["sessions"][story_id]
```

### Shared State

All worktrees read/write the same `state.json` via absolute path (configured in `config.yaml`). Access is file-locked via `FileManager` + `FileLock`.

```
Main worktree (~/avaris-ai/)
  └─ .claude/hooks/workflow/state.json  ← single source of truth
       ▲         ▲         ▲
  Worktree 1  Worktree 2  Worktree 3
```

### Orchestration Control

The user runs Claude in the **main worktree** (no `--worktree`) and controls sessions via `state.json` control flags:

| Action | How | Effect |
|---|---|---|
| Monitor | Read `state.json` | See all session statuses and phases |
| Hold | `session.control.hold = true` | `hold_checker.py` blocks agents/skills (Read/Write/Bash still allowed) |
| Gate | `session.control.blocked_until_phase = "review"` | `phase_guard.py` blocks entry to that phase |
| Abort | `session.control.status = "aborted"` | `hold_checker.py` blocks all agents/skills |
| Release | Clear hold/blocked flags | Session resumes normally |

### Session Context Directory

Each session writes artifacts to a shared directory in the main worktree:

```
.claude/sessions/SPRINT-001/
├── SK-001/
│   ├── log.jsonl          ← Phase transitions, agent invocations, scores
│   ├── escalations.jsonl  ← Blocked phases, CI failures, max iterations
│   ├── reviews/
│   │   ├── code-review-1.md
│   │   └── code-review-2.md
│   └── reports/
│       ├── test-report.md
│       └── ci-report.md
├── SK-002/
│   └── ...
└── summary.md             ← Sprint-level aggregation (generated by main)
```

Log entry format:
```json
{"ts": "2026-03-10T14:30:00Z", "session": "SK-001", "event": "phase_enter", "phase": "code", "from": "pre-coding"}
{"ts": "2026-03-10T14:45:00Z", "session": "SK-001", "event": "validation", "confidence": 85, "quality": 78, "iteration": 1}
```

Written by `session_logger.py` (PostToolUse) — logs phase transitions, agent invocations, and validation scores.

### Worktree Cleanup

| Trigger | When | Action |
|---|---|---|
| Auto | After `/push` + CI green | `cleanup_trigger.py` removes session worktree |
| Manual | User runs `cleanup_worktrees.py` | Remove all worktrees with merged branches |
| Build | `/build` start | Remove stale worktrees from previous sprints |

---

## State Design

Single `state.json` in the main worktree. Two levels: **global** (top-level) and **per-session** (under `sessions`).

### Shape

```json
{
  "workflow_active": true,

  "sessions": {
    "SK-001": {
      "session_id": "abc-123-uuid",
      "workflow_type": "implement",
      "story_id": "SK-001",

      "phase": {
        "current": "review",
        "previous": "code",
        "recent_agent": "code-reviewer"
      },
      "control": {
        "status": "running",
        "hold": false,
        "blocked_until_phase": null
      },
      "pr": {
        "created": false,
        "number": null
      },
      "validation": {
        "decision_invoked": true,
        "confidence_score": 65,
        "quality_score": 72,
        "iteration_count": 1,
        "escalate_to_user": false
      },
      "ci": {
        "status": "pending",
        "iteration_count": 0,
        "escalate_to_user": false
      }
    },

    "PR-42": {
      "session_id": "ghi-789-uuid",
      "workflow_type": "pr-review",
      "pr_number": 42,

      "phase": {
        "current": "pr-review",
        "previous": null,
        "recent_agent": "code-reviewer"
      },
      "control": {
        "status": "running",
        "hold": false,
        "blocked_until_phase": null
      },
      "pr": {
        "created": true,
        "number": 42
      },
      "validation": {
        "decision_invoked": true,
        "confidence_score": 55,
        "quality_score": 60,
        "iteration_count": 1,
        "escalate_to_user": false
      },
      "ci": null
    }
  }
}
```

### Field Reference

**Global**: `workflow_active` (boolean) — when false, all hooks short-circuit.

**Session keys**: Story ID for implement (e.g. `SK-001`), `PR-{number}` for review (e.g. `PR-42`).

| Group | Field | Type | Description |
|---|---|---|---|
| root | `session_id` | string | Claude Code session UUID (audit) |
| root | `workflow_type` | `"implement"` / `"pr-review"` | Workflow type |
| root | `story_id` | string | Story ID (implement only) |
| root | `pr_number` | integer | PR number (pr-review only) |
| `phase` | `current` | string | Current phase |
| `phase` | `previous` | string / null | Previous phase (for guard validation) |
| `phase` | `recent_agent` | string / null | Last agent invoked |
| `control` | `status` | `"running"` / `"completed"` / `"failed"` / `"aborted"` | Lifecycle status |
| `control` | `hold` | boolean | Blocks agents/skills when true |
| `control` | `blocked_until_phase` | string / null | Blocks entry to this phase |
| `pr` | `created` | boolean | PR exists |
| `pr` | `number` | integer / null | PR number |
| `validation` | `decision_invoked` | boolean | `/decision` was called |
| `validation` | `confidence_score` | integer (0-100) | Reviewer confidence |
| `validation` | `quality_score` | integer (0-100) | Code quality assessment |
| `validation` | `iteration_count` | integer | Review-refactor cycles completed |
| `validation` | `escalate_to_user` | boolean | Max iterations reached |
| `ci` | `status` | `"pending"` / `"pass"` / `"fail"` | CI check status (null for pr-review) |
| `ci` | `iteration_count` | integer | CI fix cycles completed |
| `ci` | `escalate_to_user` | boolean | Max CI iterations reached |

### Access Pattern

```python
story_id = os.environ["STORY_ID"]
session = state["sessions"][story_id]

# Phase guard
session["phase"]["current"]
session["control"]["hold"]

# Validation loop
session["validation"]["confidence_score"]
session["validation"]["iteration_count"]

# Main orchestrator
for key, s in state["sessions"].items():
    print(f"{key}: {s['control']['status']} @ {s['phase']['current']}")
```

---

## Hook Registry

### settings.local.json — Global Hooks

| Event | Matcher | Script | Purpose |
|---|---|---|---|
| `UserPromptSubmit` | — | `build_entry.py` | `/build` → launch sessions |
| `UserPromptSubmit` | — | `implement_trigger.py` | `/implement` → activate workflow, create session dir |
| `UserPromptSubmit` | — | `review_trigger.py` | `/review` → initialize PR-review session |
| `PreToolUse` | `Agent` | `pre_coding_phase.py` | Enforce Explore → Plan → plan-reviewer order |
| `PreToolUse` | `Agent` | `code_phase.py` | Enforce test-engineer → test-reviewer order |
| `PreToolUse` | `Agent` | `hold_checker.py` | Block agents if session held/aborted |
| `PreToolUse` | `Skill` | `decision_handler.py` | Intercept `/decision`, write scores |
| `PreToolUse` | `Skill` | `hold_checker.py` | Block skills if session held/aborted |
| `PreToolUse` | `Bash` | `bash_guard.py` | Guard PR ops + git push (see below) |
| `PostToolUse` | — | `recorder.py` | Record phase/agent to state |
| `PostToolUse` | — | `reminders.py` | Inject contextual markdown reminders |
| `PostToolUse` | — | `session_logger.py` | Append to session log.jsonl |
| `PostToolUse` | `Write` | `simplify_trigger.py` | Auto `/simplify` on new files |
| `PostToolUse` | `Bash` | `pr_recorder.py` | Detect `gh pr create`, record PR number |
| `PostToolUse` | `Skill` | `ci_check_handler.py` | After `/push` → poll CI, fix loop |
| `PostToolUse` | `Skill` | `cleanup_trigger.py` | Remove merged worktrees |
| `Stop` | — | `stop_guard.py` | Block unless Done + PR + CI green; write "completed" on allow |

#### bash_guard.py

```
├─ 'gh pr create' in command?  → BLOCK unless phase == 'create-pr'
├─ 'gh pr (close|merge|edit)'? → BLOCK always (destructive mutations)
├─ 'git push' in command?      → BLOCK unless phase == 'push'
└─ Everything else             → ALLOW (view, list, checks always ok)
```

### code-reviewer.md — Agent Frontmatter Hooks

Stop hooks (auto-converted to SubagentStop):

| Script | Purpose |
|---|---|
| `decision_guard.py` | Block stop unless `/decision` was invoked |
| `validation_loop.py` | Check scores → allow, refactor, or escalate |
| `escalate.py` | Surface escalation to user at max iterations |

### Skill Frontmatter — Phase Guards

See [Phase Enforcement](#phase-enforcement) for the full table and example.

### Reminders

`reminders.py` maps `(event, tool, agent)` tuples to markdown templates injected as `systemMessage`:

| Trigger | Template |
|---|---|
| PostToolUse + EnterPlanMode | `pre_coding_phase.md` |
| PostToolUse + Agent(Plan) | `plan_review.md` |
| PostToolUse + ExitPlanMode | `coding_phase.md` |
| PostToolUse + Agent(test-engineer) | `test_review.md` |
| PreToolUse + Agent(code-reviewer) | `code-reviewer.md` |

---

## Directory Structure

```
.claude/hooks/workflow/
├── hook.py                  # Base Hook class (stdin, block/success/debug output)
├── config.py                # YAML config loader (dot-notation, cached)
├── config.yaml              # Phases, agents, thresholds, paths
├── workflow_gate.py         # Global on/off switch
├── state_store.py           # File-locked JSON state persistence
├── initialize_state.py      # Reset state on session start
├── paths.py                 # Sprint/session path builder
│
├── constants/
│   └── phases.py            # Phase names, status constants
│
├── models/
│   ├── hook_input.py        # Pydantic models for hook event inputs
│   └── hook_output.py       # Pydantic models for hook outputs
│
├── guards/
│   ├── phase_guard.py       # Shared: validate predecessor + record transition
│   ├── pre_coding_phase.py  # Enforce Explore → Plan → plan-reviewer
│   ├── code_phase.py        # Enforce test-engineer → test-reviewer
│   ├── hold_checker.py      # Block agents/skills if held or aborted
│   ├── bash_guard.py        # Guard PR creation, PR mutation, git push
│   └── stop_guard.py        # Block stop unless Done + PR + CI green
│
├── handlers/
│   ├── build_entry.py       # /build → launch sessions
│   ├── implement_trigger.py # /implement → activate workflow + create session dir
│   ├── review_trigger.py    # /review → initialize PR-review session
│   ├── recorder.py          # Record phase, agent to state
│   ├── reminders.py         # Inject markdown reminders
│   ├── session_logger.py    # Append to session log.jsonl
│   ├── pr_recorder.py       # Detect gh pr create, record PR number
│   ├── record_done.py       # Record story completion
│   ├── simplify_trigger.py  # Auto /simplify on new files
│   ├── refactor.py          # Trigger /refactor from review loop
│   ├── ci_check_handler.py  # Poll CI after /push, fix loop
│   └── cleanup_trigger.py   # Remove merged worktrees
│
├── validation/
│   ├── decision_handler.py  # Intercept /decision, write scores
│   ├── decision_guard.py    # Block reviewer stop unless /decision invoked
│   ├── validation_loop.py   # Check scores → allow/refactor/escalate
│   ├── escalate.py          # Surface escalation to user
│   └── validation_log.py    # Append to validation.log
│
├── lib/
│   ├── file_manager.py      # Atomic writes, file-locking
│   ├── context_injector.py  # Template loader/renderer
│   ├── parallel_session.py  # Launch parallel sessions via WSL/cmd.exe
│   └── launch-claude.py     # Tmux orchestrator (claude --worktree)
│
├── utils/
│   └── order_validation.py  # Generic ordered-list validator
│
└── templates/reminders/
    ├── pre_coding_phase.md
    ├── coding_phase.md
    ├── plan_review.md
    ├── test_review.md
    └── code-reviewer.md
```

---

## Design Decisions

1. **Two workflows, one entry point**: `/build` routes to Implement or PR-Review based on whether open PRs exist.
2. **Decentralized phase guards**: Each phase owns its guard in skill frontmatter via shared `phase_guard.py`. PR-Review has no phase guards.
3. **File-locked shared state**: All mutations go through `FileManager` + `FileLock` for concurrent worktree access.
4. **Workflow gate**: Every hook checks `workflow_active` first — entire system toggles off without removing hooks.
5. **Shared validation loop**: Both workflows use the same decision_guard + validation_loop + escalate chain.
6. **Escalation over blocking**: Validation loops escalate to user after max iterations rather than blocking indefinitely.
7. **CI early escalation**: CI fix attempts capped at 2 (not 3) — CI failures are often not auto-fixable.
8. **Bash guardrails**: Single `bash_guard.py` blocks `gh pr create`, destructive PR mutations, and `git push` outside their designated phases.
9. **Main as orchestrator**: User controls worktree sessions via hold/blocked/abort flags in state.json.
10. **Story-based tmux sessions**: Each story gets its own tmux session named after story ID.
11. **Session context directory**: Persistent audit trail in `.claude/sessions/SPRINT-NNN/STORY-ID/`.
12. **Config-driven**: Phases, agents, thresholds, reminders all in `config.yaml`.

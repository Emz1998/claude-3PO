# claude-3PO — Aggressive Subtraction Plan

## Context

You built claude-3PO top-down without using any of the three workflows (build/specs/implement), 29 commands, or 10 guardrails. That's a mistake you've named — scope was speculative, not earned. This plan strips the repo to the smallest thing you can actually *use*, then lets real usage decide what grows back.

**End state**: one workflow, ~5 commands, 3 guardrails, no slices, no project_manager, no headless. The dispatcher/state-store bones stay because they're clean and cheap. Everything else gets deleted.

## Proposed New Workflow — `Flow`

Replace build/specs/implement with one workflow, four phases:

```
/plan   →   /code   →   /review   →   /done
 ↑                          ↓
 └─── /revise (loops back) ─┘
```

- **plan** — user invokes `/plan`. Claude explores (one or two Agents via agent_guard) then writes a plan. User approves via `/code` (advance) or `/revise` (loop).
- **code** — write tests + implementation. No auto-phase, no TDD skip. User decides when to advance.
- **review** — run quality checks + code-review agent. Pass → `/done`. Fail → `/revise` loops back to code.
- **done** — PR/CI are *optional manual steps*, not phases. Git already tracks them.

Five commands total: `/plan`, `/code`, `/review`, `/revise`, `/done`. Maybe a `/reset`.

## What Stays (the bones)

| Area | Files | Why |
|------|-------|-----|
| Dispatchers | `scripts/dispatchers/` (all 8) | Clean hook entry points, ~80 LOC each. Untouched. |
| `phase_guard` | `handlers/guardrails/phase_guard.py` | Core drift-prevention. Rewrite against new 4-phase list. |
| `agent_guard` | `handlers/guardrails/agent_guard.py` | Count limits genuinely useful. |
| `stop_guard` | `handlers/guardrails/stop_guard.py` | Prevents premature session end. |
| State facade | `lib/state_store/store.py` + new `base.py` | Pattern is good; just shrink base.py and drop slices. |
| Models | `models/state.py` | Keep; prune fields for deleted features. |
| Hooks config | `hooks/hooks.json` | Keep wiring. |
| Tests | `scripts/tests/` | Keep the tests for things that survive; delete the rest. |

## What Gets Deleted

| Path | LOC | Reason |
|------|-----|--------|
| `scripts/handlers/guardrails/write_guard.py` | 341 | Redundant with phase_guard + plan sections |
| `scripts/handlers/guardrails/edit_guard.py` | 305 | Same — phase controls what's editable |
| `scripts/handlers/guardrails/command_validator.py` | 189 | Duplicates `settings.json` permissions |
| `scripts/handlers/guardrails/webfetch_guard.py` | 115 | Weak defense, low catch rate |
| `scripts/handlers/guardrails/task_create_tool_guard.py` | 154 | TaskCreate is low-risk |
| `scripts/handlers/guardrails/task_created_guard.py` | 228 | Same |
| `scripts/handlers/guardrails/agent_report_guard.py` | 234 | Scoring/verdict validation is ceremony |
| `scripts/handlers/headless/` + prompts | — | Plan mode + AskUserQuestion covers clarify |
| `scripts/utils/resolver.py` | 698 | Auto-phase orchestration gone; user advances manually |
| `scripts/utils/validator.py` | 1221 | Specs-only; specs workflow gone |
| `scripts/lib/state_store/build.py` | 282 | Workflow slices collapse into one base |
| `scripts/lib/state_store/implement.py` | 282 | Same |
| `scripts/lib/state_store/specs.py` | — | Same |
| `scripts/dispatchers/post_tool_use_failure.py` | 62 | TDD-style auto-recording — not in new flow |
| `scripts/dispatchers/task_created.py`, `task_completed.py`, `task_create_tool_guard` wiring | ~160 | No TaskCreate guarding |
| `claude-3PO/commands/*` except the 5 new ones | ~24 files | Command sprawl |
| `claude-3PO/agents/` — keep only 2 (research, code-reviewer) | ~5 files | Drop product-owner, plan-review, qa-specialist, architect, test-reviewer until a real need shows up |
| `claude-3PO/templates/architecture.md`, `product-vision.md`, `backlog.*`, `visionize-questions.md`, `clarity-review.md` | ~60KB | Specs workflow gone |
| `claude-3PO/project_manager/` | ~2.5K LOC | GitHub sync is a separate product; revive if needed |
| `E2E_SPECS_TEST_REPORT.md` | 14KB | Artifact of a workflow being deleted |

**Estimated deletion**: ~8K LOC + 24 commands + 5 agents + 6 templates + entire project_manager.

## What Gets Simplified

**`base.py`** (2509 LOC → target ~300):
After slices are gone, base.py only needs: session I/O + filelock, phases list, plan text, review verdict, agents log. Everything else (PR/CI/code_files/tests accessors) goes.

**`phase_guard.py`** (422 LOC → ~120):
New phase list is 4 items. No review-exhaustion map. No special-skill handling beyond `/continue`, `/revise`, `/reset`.

**`agent_guard.py`** — keep count limits, simplify to a single `{phase → max}` dict.

**`config.json`** — collapse workflow definitions to one.

## Execution Order

Each step is its own PR, TDD per CLAUDE.md. Stop and use the system for a few days after Step 4 before continuing.

1. **Delete the unused workflows** — remove build/specs/implement-specific code: state slices, specs validator, headless, project_manager, resolver. Update `dispatchers/post_tool_use.py` imports. Tests for deleted modules: delete.
2. **Shrink `base.py`** — delete unused accessors (PR, CI, code_files, code_review, tests, plan_review, test_review, task hierarchy). Keep phase + plan + agents + violations.
3. **Rewrite `phase_guard.py`** around the new 4-phase list. Drop the review-checkpoint map.
4. **Prune commands + agents + templates** — keep only the 5 new commands, 2 agents, 0 templates (or 1 generic plan template if useful).
5. **(Pause, use it for a week.)** On real tasks. Note what you miss. Then:
6. **Re-add only what's missed**, one feature at a time, each tied to a concrete observation from Step 5.

## Critical Files

- `scripts/lib/state_store/base.py` — big shrink
- `scripts/lib/state_store/store.py` — drop slice wiring
- `scripts/handlers/guardrails/phase_guard.py` — rewrite
- `scripts/handlers/guardrails/__init__.py:163` — shrink `TOOL_GUARDS` map to 2 entries (Skill, Agent)
- `scripts/dispatchers/post_tool_use.py` — remove resolver call
- `scripts/config/config.json` — single workflow
- `claude-3PO/commands/` — delete most
- `claude-3PO/hooks/hooks.json` — remove hooks for deleted dispatchers

## Verification

The real test is usage, not unit tests. After Step 4:

1. `pytest scripts/tests/` green on the reduced suite.
2. Run a real task end-to-end: `/plan` a small fix, `/code` it, `/review`, `/done`. Confirm phase_guard blocks out-of-order invocation.
3. Confirm `agent_guard` stops a 4th Agent call in plan phase.
4. Confirm `stop_guard` refuses session end before `/review` passes.
5. **Use it for a week on actual work.** Journal what's missing. That journal drives Step 6.

## Anti-Goals

- Do **not** re-add guardrails speculatively. Only add one when you can name the specific drift it would have caught in the past week.
- Do **not** re-introduce three workflows. If Flow doesn't fit a task, that's data for the plan — don't fork a new workflow to handle it.
- Do **not** rebuild project_manager inside the repo. GitHub sync is a separate tool.

## Open Questions (resolve before Step 1)

- Are you ok deleting `project_manager/` outright, or should it move to a separate archived branch/repo first?
- Keep `templates/constitution.md` (you might still use it as a prompt template)?
- Any commands outside the 5 proposed that you've actually typed, even once?

# Plan: CODEBASE.md Gate in Explore Phase

## Context

The explore phase launches 5 agents (3 Explore + 2 Research). Their findings (`last_assistant_message`) are currently discarded — only completion status is tracked. We want to:
1. Collect all agent findings during explore
2. Add a `write-codebase` sub-phase after all agents complete but before `plan`
3. Block the plan phase until `CODEBASE.md` is written using the collected findings
4. Inject the collected findings as context so the main agent can write `CODEBASE.md`

## Approach

### Step 1: Store agent findings in state during SubagentStop

In `recorder.py` → `record_subagent_stop()`, save each Explore/Research agent's `last_assistant_message` to state:

```python
# Inside _process, after _mark_first_running_completed:
if agent_type in ("Explore", "Research") and phase == "explore":
    findings = state.setdefault("agent_findings", [])
    findings.append({
        "agent_type": agent_type,
        "message": last_message,
    })
```

### Step 2: Add `write-codebase` phase transition

In `recorder.py` → `record_subagent_stop()`, when all agents are done, advance to `write-codebase` instead of `plan`:

```python
# Change: state["phase"] = "plan"  →  state["phase"] = "write-codebase"
if all_done:
    state["phase"] = "write-codebase"
```

### Step 3: Guard the `write-codebase` phase

In `guards/write_guard.py` → `validate_pre()`, allow only `CODEBASE.md` writes during this phase:

```python
if phase == "write-codebase":
    if file_path.endswith("CODEBASE.md"):
        return "allow", ""
    return "block", "Only CODEBASE.md may be written during 'write-codebase' phase."
```

In `guards/agent_guard.py`, block all agents during `write-codebase` (it falls through to the catch-all block at the bottom — no change needed).

### Step 4: Advance from `write-codebase` → `plan` on PostToolUse Write

In `recorder.py` → `record_write()`, add:

```python
if phase == "write-codebase" and file_path.endswith("CODEBASE.md"):
    def _advance(s: dict) -> None:
        s["codebase_written"] = True
        s["phase"] = "plan"
    store.update(_advance)
    return "allow", ""
```

### Step 5: Inject findings as context via reminder

In `reminder.py`, add a phase transition reminder for `write-codebase` that includes the collected `agent_findings` from state:

```python
PHASE_TRANSITION_REMINDERS["write-codebase"] = ... # dynamic, see below
```

Since this needs to be dynamic (includes findings), handle it in `get_phase_transition_reminder()`:

```python
if phase == "write-codebase":
    findings = state.get("agent_findings", [])
    sections = []
    for i, f in enumerate(findings, 1):
        sections.append(f"### {f['agent_type']} Agent {i}\n{f['message']}")
    findings_text = "\n\n".join(sections)
    return (
        "All exploration complete. Write CODEBASE.md using the findings below.\n\n"
        f"{findings_text}"
    )
```

### Step 6: Initialize state fields

In `guards/skill_guard.py` → `_initial_state()`, add:
- `"agent_findings": []`
- `"codebase_written": False`

### Step 7: Update dry runs and tests

- Update `subagent_stop_payload()` in both dry runs to include realistic `last_assistant_message` content
- Add a `write-codebase` step in the dry run flow: write CODEBASE.md between explore completion and plan phase
- Update `test_agent_guard.py` to verify agents are blocked in `write-codebase` phase
- Update `test_recorder.py` to verify `agent_findings` storage and `write-codebase` → `plan` transition

## Files to Modify

| File | Change |
|------|--------|
| `recorder.py` | Store `agent_findings` on SubagentStop; advance to `write-codebase` instead of `plan`; advance `write-codebase` → `plan` on CODEBASE.md write |
| `guards/write_guard.py` | Allow only `CODEBASE.md` in `write-codebase` phase |
| `guards/skill_guard.py` | Add `agent_findings: []` and `codebase_written: False` to initial state |
| `reminder.py` | Add dynamic `write-codebase` reminder with collected findings |
| `tests/test_recorder.py` | Test `agent_findings` storage, `write-codebase` transition, CODEBASE.md write advancing to `plan` |
| `tests/test_agent_guard.py` | Add `write-codebase` to blocked phases parametrize list |
| `dry_runs/implement_dry_run.py` | Add `write-codebase` step with CODEBASE.md write |
| `dry_runs/plan_dry_run.py` | Same |

## Verification

1. `python -m pytest .claude/hooks/workflow/tests/ -v` — all tests pass
2. `python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py` — 0 failures
3. `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py` — 0 failures
4. `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd --story-id SK-123` — 0 failures

# Plan: Add logger.py Module for Workflow Debugging

## Context

During e2e testing of the workflow hooks, there's no way to observe what's happening — which events fired, what guardrail/recorder decided, what phase transitions occurred, what reminders were sent. Debugging requires guessing or adding print statements. A logger module called from each dispatcher would write a structured log file for real-time observation.

## Approach

- **`logger.py`** — in-process module (not a CLI) imported by dispatchers, writes to a log file
- Each dispatcher calls `logger.log()` at every key point: event received, guardrail decision, recorder action, phase transition, reminder sent, blocks, errors
- Log file at `.claude/hooks/workflow/workflow.log`
- Always on — full observability of the workflow system
- JSONL format (one JSON object per line) for easy `tail -f` and parsing

## Files to Modify

| File | Change |
|------|--------|
| `.claude/hooks/workflow/logger.py` | New file — `log()` function, file writing |
| `.claude/hooks/workflow/dispatchers/pre_tool_use.py` | Add log calls |
| `.claude/hooks/workflow/dispatchers/post_tool_use.py` | Add log calls |
| `.claude/hooks/workflow/dispatchers/subagent_stop.py` | Add log calls |
| `.claude/hooks/workflow/dispatchers/task_created.py` | Add log calls |
| `.claude/hooks/workflow/dispatchers/user_prompt_submit.py` | Add log calls |
| `.claude/hooks/workflow/dispatchers/stop.py` | Add log calls |

## Steps

### Step 1: Create logger.py

```python
"""logger.py — Workflow event logger for full observability.

Writes JSONL to workflow.log. Always on.
Use `tail -f .claude/hooks/workflow/workflow.log` to observe.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "workflow.log"


def log(event: str, **kwargs) -> None:
    """Append a structured log entry to workflow.log."""
    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "event": event,
        **kwargs,
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

### Step 2: Add log calls to each dispatcher

Each dispatcher logs at every decision point. Pattern: `log("Event:action", key=value)`.

**pre_tool_use.py:**
```python
from workflow.logger import log

# After guardrail decision:
log("PreToolUse", tool=tool_name, decision=decision)

# On block:
log("PreToolUse:block", tool=tool_name, reason=reason)

# After agent recorded:
log("PreToolUse:Agent:recorded", agent_type=...)

# After reminder sent:
log("PreToolUse:reminder", reminder=reminder_text[:100])
```

**post_tool_use.py:**
```python
from workflow.logger import log

# Skill guardrail decision:
log("PostToolUse:Skill", decision=decision)

# Skill block:
log("PostToolUse:Skill:block", reason=reason)

# After recorder:
log("PostToolUse:recorded", tool=tool_name)

# After reminder sent:
log("PostToolUse:reminder", tool=tool_name, reminder=reminder_text[:100])
```

**subagent_stop.py:**
```python
from workflow.logger import log

# After recorder (phase may have advanced):
log("SubagentStop:recorded", agent_type=agent_type)

# After reminder sent:
log("SubagentStop:reminder", agent_type=agent_type, reminder=reminder_text[:100])
```

**task_created.py:**
```python
from workflow.logger import log

# After guardrail decision:
log("TaskCreated", decision=decision, subject=raw_input.get("task_subject", ""))

# On block:
log("TaskCreated:block", reason=reason)

# After recorder:
log("TaskCreated:recorded")
```

**user_prompt_submit.py:**
```python
from workflow.logger import log

# After guardrail decision:
log("UserPromptSubmit", prompt=prompt[:80], decision=decision)

# On block:
log("UserPromptSubmit:block", reason=reason)

# After reminder sent:
log("UserPromptSubmit:reminder", reminder=EXPLORE_KICKOFF[:100])
```

**stop.py:**
```python
from workflow.logger import log

# After guardrail decision:
log("Stop", decision=decision)

# On block:
log("Stop:block", reason=reason)
```

### Step 3: Add tests

Test that `log()` is a no-op when disabled and writes entries when enabled.

## Files to Modify

| File | Change |
|------|--------|
| `.claude/hooks/workflow/logger.py` | New file |
| `.claude/hooks/workflow/dispatchers/*.py` | Add log calls (6 files) |
| `.claude/hooks/workflow/tests/test_logger.py` | New test file |

## Verification

1. Run tests: `python3 -m pytest tests/test_logger.py -v`
2. Run full suite: `python3 -m pytest tests/ --ignore=tests/test_file_manager.py -q`
3. Run `/implement` and observe in another terminal:
   ```
   tail -f .claude/hooks/workflow/workflow.log
   ```
4. Verify log entries appear for: blocks, allows, recorder actions, reminders, phase transitions
5. Example expected output:
   ```jsonl
   {"ts":"2026-04-01T15:30:00.123","event":"UserPromptSubmit","prompt":"/implement SK-001","decision":"allow"}
   {"ts":"2026-04-01T15:30:00.456","event":"UserPromptSubmit:reminder","reminder":"Phase: EXPLORE. Launch 3 Explore + 2 Research agents in par..."}
   {"ts":"2026-04-01T15:30:01.789","event":"PreToolUse","tool":"Agent","decision":"allow"}
   {"ts":"2026-04-01T15:30:01.890","event":"PreToolUse:Agent:recorded","agent_type":"Explore"}
   {"ts":"2026-04-01T15:30:05.000","event":"SubagentStop:recorded","agent_type":"Explore"}
   {"ts":"2026-04-01T15:30:05.100","event":"SubagentStop:reminder","agent_type":"Explore","reminder":"All exploration complete. Launch a Plan agent to design..."}
   ```

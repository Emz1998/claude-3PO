# Handlers

Consolidated entry points that route hook events to the appropriate guards, trackers, and validators.

## Files

| File | Purpose |
|------|---------|
| `user_prompt.py` | UserPromptSubmit: workflow activation, dry run, validation detection |
| `pre_tool.py` | PreToolUse: routes to guards based on tool name |
| `post_tool.py` | PostToolUse: routes to trackers based on tool name |
| `subagent_stop.py` | SubagentStop: deliverables enforcement before stop |

## Event Routing

### UserPromptSubmit (`user_prompt.py`)
- Detects `/implement` command to activate workflow
- Detects `/deactivate-workflow` to deactivate
- Reads validation flags and sets `pending_validation`

### PreToolUse (`pre_tool.py`)
- **Skill tool** -> `PhaseTransitionGuard` + `ReleasePlanTracker.run_pre_tool`
- **Task tool** -> `SubagentAccessGuard`

### PostToolUse (`post_tool.py`)
- **Skill tool** -> `PhaseTracker` + `ContextInjector` + `DeliverableTracker` + `ReleasePlanTracker.run_post_tool`
- **Write/Edit/Read/Bash** -> `DeliverableTracker`

### SubagentStop (`subagent_stop.py`)
- Runs `DeliverablesExitGuard` to check deliverable completion

## Key Exports

- `UserPromptHandler` / `handle_user_prompt()`
- `PreToolHandler` / `handle_pre_tool()`
- `PostToolHandler` / `handle_post_tool()`
- `SubagentStopHandler` / `handle_subagent_stop()`

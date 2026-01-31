#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.state import get_state, is_workflow_active  # type: ignore
from lib.guardrails import load_config, check_can_stop  # type: ignore

input_data = json.load(sys.stdin)

# Prevent infinite loops
if input_data.get("stop_hook_active"):
    sys.exit(0)

# Skip if workflow not active
if not is_workflow_active():
    sys.exit(0)

config = load_config("workflow")
state = get_state()

# Validate subagent can stop based on stop_conditions
allowed, reason = check_can_stop(config, state, "subagent")
if not allowed:
    print(json.dumps({"decision": "block", "reason": reason}))

sys.exit(0)

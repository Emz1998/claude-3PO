#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Literal, Optional
import json


@dataclass
class UpdatedInput:
    field_to_modify: str


@dataclass
class HookSpecificOutput:
    hook_event_name: Literal["PreToolUse",]
    permission_decision: Optional[Literal["allow", "deny", "ask"]] = None
    permission_decision_reason: Optional[str] = None
    updated_input: Optional[UpdatedInput] = None
    additional_context: Optional[str] = None


@dataclass
class Output:
    _continue: Optional[bool] = None
    stop_reason: Optional[str] = None
    suppress_output: Optional[bool] = None
    system_message: Optional[str] = None
    decision: Optional[Literal["block", "allow"]] = None
    reason: Optional[str] = None
    hook_specific_output: Optional[HookSpecificOutput] = None

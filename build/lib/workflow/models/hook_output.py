from typing import Literal
from pydantic import BaseModel, Field


class GeneralHSO(BaseModel):
    hook_event_name: Literal["PostToolUse", "UserPromptSubmit", "Stop"]
    additional_context: str | None = None


class PreToolUseHSO(BaseModel):
    hook_event_name: Literal["PreToolUse"] = "PreToolUse"
    permission_decision: Literal["allow", "deny", "ask"] = "allow"
    permission_decision_reason: str | None = None
    updated_input: dict[str, str] | None = None
    additional_context: str | None = None


class PermissionRequestHSODecision(BaseModel):
    behavior: Literal["allow", "deny"] = "allow"
    updated_input: dict[str, str] | None = None


class PermissionRequestHSO(BaseModel):
    hook_event_name: Literal["PermissionRequest"] = "PermissionRequest"
    decision: PermissionRequestHSODecision = Field(
        default_factory=PermissionRequestHSODecision
    )


class BaseOutput(BaseModel):
    continue_: bool | None = Field(default=None, alias="continue")
    stop_reason: str | None = None
    suppress_output: bool | None = None
    system_message: str | None = None


class DecisionControl(BaseOutput):
    decision: Literal["block", "allow"] = "allow"
    reason: str | None = None


class PreToolUseOutput(BaseOutput):
    hook_specific_output: PreToolUseHSO


class PostToolUseOutput(DecisionControl):
    hook_specific_output: GeneralHSO


class StopOutput(DecisionControl):
    hook_specific_output: GeneralHSO


class UserPromptSubmitOutput(DecisionControl):
    hook_specific_output: GeneralHSO

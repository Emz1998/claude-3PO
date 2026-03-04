from typing import (
    ClassVar,
    Generic,
    TypeVar,
    Any,
    get_args,
    get_origin,
    cast,
    Self,
)


import sys
import json
from dataclasses import dataclass
from workflow.models.hook_input import (
    PreToolUseInput,
    PostToolUseInput,
    UserPromptSubmitInput,
    StopInput,
    ToolInputType,
    BashTool,
    SkillTool,
)
from workflow.models.hook_output import (
    PreToolUseOutput,
    PreToolUseHSO,
    GeneralHSO,
    PostToolUseOutput,
    UserPromptSubmitOutput,
    StopOutput,
)

# Marker classes for Generic type parameter
ToolType = TypeVar("ToolType", bound=ToolInputType)


HookInputType = (
    PreToolUseInput[ToolType]
    | PostToolUseInput[ToolType]
    | UserPromptSubmitInput
    | StopInput
)
HookOutputType = (
    PreToolUseOutput | PostToolUseOutput | UserPromptSubmitOutput | StopOutput
)


def read_stdin() -> dict[str, Any]:
    return json.loads(sys.stdin.read())


@dataclass
class HookEvent:
    """Base class providing create() from stdin."""

    input: Any
    output: Any

    @classmethod
    def _input_type(cls) -> Any:
        raise NotImplementedError

    @classmethod
    def _default_output(cls) -> Any:
        raise NotImplementedError

    @classmethod
    def create(cls) -> Self:
        data = read_stdin()
        input_ = cls._input_type().model_validate(data)
        return cls(input=input_, output=cls._default_output())


@dataclass
class PreToolUse(HookEvent, Generic[ToolType]):
    input: PreToolUseInput[ToolType]
    output: PreToolUseOutput

    @classmethod
    def _input_type(cls) -> type:
        return PreToolUseInput[ToolInputType]

    @classmethod
    def _default_output(cls) -> PreToolUseOutput:
        return PreToolUseOutput(hook_specific_output=PreToolUseHSO())


@dataclass
class PostToolUse(HookEvent, Generic[ToolType]):
    input: PostToolUseInput[ToolType]
    output: PostToolUseOutput

    @classmethod
    def _input_type(cls) -> type:
        return PostToolUseInput[ToolInputType]

    @classmethod
    def _default_output(cls) -> PostToolUseOutput:
        return PostToolUseOutput(
            hook_specific_output=GeneralHSO(hook_event_name="PostToolUse")
        )


@dataclass
class UserPromptSubmit(HookEvent):
    input: UserPromptSubmitInput
    output: UserPromptSubmitOutput

    @classmethod
    def _input_type(cls) -> type:
        return UserPromptSubmitInput

    @classmethod
    def _default_output(cls) -> UserPromptSubmitOutput:
        return UserPromptSubmitOutput(
            hook_specific_output=GeneralHSO(hook_event_name="UserPromptSubmit")
        )


@dataclass
class Stop(HookEvent):
    input: StopInput
    output: StopOutput

    @classmethod
    def _input_type(cls) -> type:
        return StopInput

    @classmethod
    def _default_output(cls) -> StopOutput:
        return StopOutput(hook_specific_output=GeneralHSO(hook_event_name="Stop"))


HookEventType = PreToolUse | PostToolUse | UserPromptSubmit | Stop
T = TypeVar("T", bound=HookEventType)

_OUTPUT_TYPE_MAP: dict[type, type] = {
    PreToolUse: PreToolUseOutput,
    PostToolUse: PostToolUseOutput,
    UserPromptSubmit: UserPromptSubmitOutput,
    Stop: StopOutput,
}


class Hook(Generic[T]):
    __orig_class__: ClassVar[type]

    @property
    def event_type(self) -> HookEventType:
        event_type = get_args(self.__orig_class__)[0]
        return get_origin(event_type) or event_type

    def create(self) -> Self:
        event = self.event_type.create()
        self._event = event
        return self

    @property
    def input(self) -> Any:
        return self._event.input

    @property
    def output(self) -> Any:
        return self._event.output

    def block(self, message: str) -> None:
        print(message)
        sys.exit(2)

    def success_response(self, message: str) -> None:
        print(message)
        sys.exit(0)

    def debug(self, message: str) -> None:
        print(message)
        sys.exit(1)

    def advanced_output(self, output: Any) -> None:
        print(json.dumps(output.model_dump()))
        sys.exit(0)

# CLAUDE.md

## Goal

- Build Claude-3PO , a workflow system with guardrails that prevent claude from drifting.

## Rules

- **IMPORTANT**:If not in plan mode and the user's request/task is too complex, present a miniplan first to the user before implementing changes. If the user's request/task is simple or trivial, skip the plan and implement changes directly.
- **IMPORTANT**: Stop and ask the user first for approval if any plan is present.
- **IMPORTANT**: Always do TDD when coding. Write/Revise tests first before implementing changes
- **IMPORTANT** Plan should always be higher level.
- **IMPORTANT**: Questions should be always asked using `AskUserQuestion` tool.
- Do not implement tasks that are beyond the scope of your plan
- If you are not sure, stop and say "I'm not sure about this task"
- Do not overcomplicate stuff. Simple/Lean approach is better than complex one
- Find and create solutions that are simple and effective.
- Always validate your work either through tests, sample ui, running a bash command, etc. Never skip any review
- Identify the README in claude-3PO that is part of your task scope and update it.
- Always make task list to track your tasks
- Before git stashing, please consult with the user.

## Coding Style

- Max of 15 lines per function.
- Make it modular and reusable as much as possible.
- Write semantic and idiomatic code. Use clear and descriptive names for variables, functions, and classes.
- Prefer readability over complexity. Write code that is easy to understand and maintain.

### Python

- Include a readable docstring with the structure below:
- **IMPORTANT**: Docstrings must include context, Args, Returns, Raises and Examples. Any missing ones are not acceptable.
- **IMPORTANT**: Add a result output in docstring's `Example`
- If sideeffect is mutating json. Specify what part of the json was updated.

```docstring without side effects
        Count non-failed agent invocations with the given name.

        Excluding failures lets retry logic check whether the name is "still
        allowed" without tripping on historical failures.

        Args:
            name (str): Agent name to count.

        Returns:
            int: Number of matching non-failed invocations.

        Example:
            >>> store.count_agents("QASpecialist")  # doctest: +SKIP
            Return: 1
```

```docstring with side effects
    """
        Replace the to-revise list and reset ``files_revised`` to empty.

        Resetting ``files_revised`` alongside makes the revision loop
        restart-safe: each new review seeds a fresh to-do/done pair.

        Args:
            files (list[str]): New to-revise file paths.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[code_files][files_to_revise]; resets files_revised.

        Example:
            >>> store.set_files_to_revise(["src/foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][files_to_revise] = ["src/foo.py"]
                state[code_files][files_revised] = []

    """

```

## Claude-3PO

### Rules

- `claude-3PO/scripts/dipatchers/` modules should only have `main()`
- `claude-3PO/scripts/handlers/` modules shouldnt have helpers. All class methods inside every modules should be public.
- Helpers should only live in either `claude-3PO/scripts/lib` or `claude-3PO/scripts/utils`
- Models should only live in `claude-3PO/scripts/models`
- `handlers/` handle all the business logic.
- `dispatchers` is the hook entry point.

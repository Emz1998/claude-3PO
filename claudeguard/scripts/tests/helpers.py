def make_hook_input(tool_name: str = "", tool_input: dict | None = None, **extra) -> dict:
    d = {"tool_name": tool_name, "tool_input": tool_input or {}}
    d.update(extra)
    return d

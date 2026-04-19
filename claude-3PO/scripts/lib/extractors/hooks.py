"""hooks.py — Extract skill and agent names from raw hook payloads.

Every function here tolerates missing keys gracefully (returning ``""``) so
guards can call them without try/except scaffolding.
"""


def strip_namespace(name: str) -> str:
    """Strip a plugin namespace prefix (``'claudeguard:explore' -> 'explore'``).

    Example:
        >>> strip_namespace("claudeguard:explore")
        'explore'
        >>> strip_namespace("explore")
        'explore'
    """
    if ":" in name:
        return name.split(":", 1)[1]
    return name


def extract_skill_name(hook_input: dict) -> str:
    """
    Extract the skill name from a hook payload, dropping any plugin namespace.

    Args:
        hook_input (dict): Raw hook event payload (must have ``tool_input.skill``).

    Returns:
        str: The bare skill name (e.g. ``"explore"``), or ``""`` if absent.

    Example:
        >>> extract_skill_name({"tool_input": {"skill": "claudeguard:explore"}})
        'explore'
    """
    raw = hook_input.get("tool_input", {}).get("skill", "")
    return strip_namespace(raw)


def extract_agent_name(hook_input: dict, key: str = "subagent_type") -> str:
    """
    Extract an agent name from a hook payload, dropping any plugin namespace.

    Two hook events carry the agent name at different paths: ``PreToolUse``
    sends ``tool_input.subagent_type``, while ``SubagentStart`` sends
    ``agent_type`` at the top level. The ``key`` argument selects which schema
    to read.

    Args:
        hook_input (dict): Raw hook event payload.
        key (str): Either ``"subagent_type"`` (default, PreToolUse) or
            ``"agent_type"`` (SubagentStart).

    Returns:
        str: The bare agent name, or ``""`` if absent.

    Example:
        >>> extract_agent_name({"tool_input": {"subagent_type": "QASpecialist"}})
        'QASpecialist'
    """
    if key == "agent_type":
        raw = hook_input.get("agent_type", "")
    else:
        raw = hook_input.get("tool_input", {}).get("subagent_type", "")
    return strip_namespace(raw)

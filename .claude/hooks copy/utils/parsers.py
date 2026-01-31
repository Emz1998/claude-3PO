def extract_slash_command_name(raw_command: str = "") -> str:
    """Extract command name from a slash-prefixed prompt."""
    if not raw_command or not raw_command.startswith("/"):
        return ""
    return raw_command[1:].split(" ")[0]

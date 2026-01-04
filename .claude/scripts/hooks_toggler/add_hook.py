#!/usr/bin/env python3
"""Register hooks in settings.local.json mirroring settings_structure.json."""

import argparse
import json
from pathlib import Path
from typing import Optional

SETTINGS_FILE = ".claude/settings.local.json"
STRUCTURE_FILE = ".claude/scripts/hooks_toggler/settings_structure.json"

VALID_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PermissionRequest",
]


def load_json(file_path: str) -> dict:
    """Load JSON file, return empty dict if missing/invalid."""
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def save_json(file_path: str, data: dict) -> None:
    """Save data to JSON file with proper formatting."""
    Path(file_path).write_text(json.dumps(data, indent=2))


def sync_structure_to_settings() -> None:
    """Sync hooks from settings_structure.json to settings.local.json."""
    structure = load_json(STRUCTURE_FILE)
    settings = load_json(SETTINGS_FILE)

    if "hooks" in structure:
        settings["hooks"] = structure["hooks"]
        save_json(SETTINGS_FILE, settings)
        print("Settings synced with structure file")


def add_hook(
    event: str,
    command: str,
    matcher: Optional[str] = None,
    timeout: int = 10,
) -> None:
    """Add a hook to both settings_structure.json and settings.local.json."""
    if event not in VALID_EVENTS:
        print(f"Error: Invalid event '{event}'")
        print(f"Valid events: {', '.join(VALID_EVENTS)}")
        return

    hook_entry = {
        "type": "command",
        "command": command,
        "timeout": timeout,
    }

    hook_group: dict = {"hooks": [hook_entry]}
    if matcher:
        hook_group["matcher"] = matcher

    # Update structure file
    structure = load_json(STRUCTURE_FILE)
    if "hooks" not in structure:
        structure["hooks"] = {e: [] for e in VALID_EVENTS}

    if event not in structure["hooks"]:
        structure["hooks"][event] = []

    # Check for duplicates
    for existing in structure["hooks"][event]:
        existing_cmd = existing.get("hooks", [{}])[0].get("command", "")
        existing_matcher = existing.get("matcher")
        if existing_cmd == command and existing_matcher == matcher:
            print(f"Hook already exists for {event}" + (f" with matcher {matcher}" if matcher else ""))
            return

    structure["hooks"][event].append(hook_group)
    save_json(STRUCTURE_FILE, structure)

    # Sync to settings.local.json
    sync_structure_to_settings()
    print(f"Hook added to {event}" + (f" with matcher {matcher}" if matcher else ""))


def remove_hook(event: str, command: str, matcher: Optional[str] = None) -> None:
    """Remove a hook from both settings_structure.json and settings.local.json."""
    if event not in VALID_EVENTS:
        print(f"Error: Invalid event '{event}'")
        return

    structure = load_json(STRUCTURE_FILE)
    if "hooks" not in structure or event not in structure["hooks"]:
        print(f"No hooks found for {event}")
        return

    original_count = len(structure["hooks"][event])
    structure["hooks"][event] = [
        h for h in structure["hooks"][event]
        if not (
            h.get("hooks", [{}])[0].get("command", "") == command
            and h.get("matcher") == matcher
        )
    ]

    if len(structure["hooks"][event]) == original_count:
        print("Hook not found")
        return

    save_json(STRUCTURE_FILE, structure)
    sync_structure_to_settings()
    print(f"Hook removed from {event}")


def list_hooks(event: Optional[str] = None) -> None:
    """List all registered hooks."""
    structure = load_json(STRUCTURE_FILE)
    hooks = structure.get("hooks", {})

    events_to_show = [event] if event else VALID_EVENTS

    for evt in events_to_show:
        if evt not in hooks:
            continue
        event_hooks = hooks[evt]
        if not event_hooks:
            continue

        print(f"\n{evt}:")
        for h in event_hooks:
            matcher = h.get("matcher", "all")
            for hook in h.get("hooks", []):
                cmd = hook.get("command", "")
                timeout = hook.get("timeout", 10)
                print(f"  - matcher: {matcher}, timeout: {timeout}s")
                print(f"    command: {cmd}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Claude hooks registration")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Add hook
    add_parser = subparsers.add_parser("add", help="Add a new hook")
    add_parser.add_argument("event", choices=VALID_EVENTS, help="Hook event type")
    add_parser.add_argument("command", help="Command to execute")
    add_parser.add_argument("-m", "--matcher", help="Tool matcher (optional)")
    add_parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout in seconds")

    # Remove hook
    rm_parser = subparsers.add_parser("remove", help="Remove a hook")
    rm_parser.add_argument("event", choices=VALID_EVENTS, help="Hook event type")
    rm_parser.add_argument("command", help="Command to match")
    rm_parser.add_argument("-m", "--matcher", help="Tool matcher (optional)")

    # List hooks
    list_parser = subparsers.add_parser("list", help="List registered hooks")
    list_parser.add_argument("event", nargs="?", choices=VALID_EVENTS, help="Filter by event")

    # Sync command
    subparsers.add_parser("sync", help="Sync structure to settings.local.json")

    args = parser.parse_args()

    if args.action == "add":
        add_hook(args.event, args.command, args.matcher, args.timeout)
    elif args.action == "remove":
        remove_hook(args.event, args.command, args.matcher)
    elif args.action == "list":
        list_hooks(args.event)
    elif args.action == "sync":
        sync_structure_to_settings()


if __name__ == "__main__":
    main()

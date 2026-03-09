#!/usr/bin/env python3
"""Manage Claude hooks: activate, deactivate, list, add, remove."""

import argparse
import json
from pathlib import Path

SETTINGS_FILE = ".claude/settings.local.json"
CACHE_FILE = ".claude/scripts/hooks_toggler/cache.json"


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


class HooksRegistry:
    def __init__(self):
        self.cache = load_json(CACHE_FILE)
        self.settings = load_json(SETTINGS_FILE)

    @property
    def current_registered_hooks(self) -> dict:
        return self.settings.get("hooks", {})

    @property
    def current_cached_hooks(self) -> dict:
        return self.cache.get("hooks", {})

    def register_new_hook(self, hooks: dict) -> None:
        self.settings["hooks"] = hooks
        save_json(SETTINGS_FILE, self.settings)
        print("Hooks registered successfully")

    def _extract_commands(self, entries: list) -> set:
        """Extract all command strings from a list of hook entries."""
        commands = set()
        for entry in entries:
            for hook in entry.get("hooks", []):
                commands.add(hook.get("command", ""))
        return commands

    def _find_new_entries(self, current_entries: list, cached_cmds: set) -> list:
        """Return entries from current that aren't already in cached commands."""
        new_entries = []
        for entry in current_entries:
            cmds = [h.get("command", "") for h in entry.get("hooks", [])]
            if any(cmd not in cached_cmds for cmd in cmds):
                new_entries.append(entry)
        return new_entries

    def _merge_event_entries(self, cached_entries: list, current_entries: list) -> list:
        """Merge entries for a single event type, deduplicating by command."""
        if not current_entries:
            return cached_entries
        if not cached_entries:
            return current_entries
        cached_cmds = self._extract_commands(cached_entries)
        new_entries = self._find_new_entries(current_entries, cached_cmds)
        return cached_entries + new_entries

    def _merge_hooks(self, cached: dict, current: dict) -> dict:
        """Merge cached hooks with any new hooks registered while deactivated."""
        all_events = set(cached.keys()) | set(current.keys())
        return {
            event: self._merge_event_entries(
                cached.get(event, []), current.get(event, [])
            )
            for event in all_events
        }

    def _set_last_action(self, action: str) -> None:
        self.cache["last_action"] = action
        save_json(CACHE_FILE, self.cache)

    @property
    def last_action(self) -> str | None:
        return self.cache.get("last_action")

    def activate_hooks(self) -> None:
        cached = self.current_cached_hooks
        current = self.current_registered_hooks
        if not cached and not current:
            print("No hooks to reactivate")
            return
        if not cached:
            print("No cached hooks to reactivate (current hooks unchanged)")
            return
        merged = self._merge_hooks(cached, current)
        self.settings["hooks"] = merged
        save_json(SETTINGS_FILE, self.settings)
        self._set_last_action("activate")
        if current:
            print("Hooks activated and merged with newly registered hooks")
        else:
            print("Hooks activated successfully")

    def cache_hooks(self) -> None:
        self.cache["hooks"] = self.current_registered_hooks
        save_json(CACHE_FILE, self.cache)

    def clear_hooks(self) -> None:
        self.settings["hooks"] = {}
        save_json(SETTINGS_FILE, self.settings)
        print("Hooks cleared successfully")

    # Commands essential in ALL events
    ESSENTIAL_COMMANDS = {
        "security/security.py",
    }

    # Commands essential only in specific events
    ESSENTIAL_PER_EVENT = {
        "UserPromptSubmit": {"skills/hooks_toggler.py"},
    }

    def _is_essential_entry(self, entry: dict, event: str) -> bool:
        """Check if a hook entry contains an essential command for the given event."""
        essential = self.ESSENTIAL_COMMANDS | self.ESSENTIAL_PER_EVENT.get(event, set())
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if any(e in cmd for e in essential):
                return True
        return False

    def _filter_essential(self, hooks: dict) -> dict:
        """Return only essential hook entries from the given hooks dict."""
        filtered = {}
        for event, entries in hooks.items():
            essential = [e for e in entries if self._is_essential_entry(e, event)]
            if essential:
                filtered[event] = essential
        return filtered

    def deactivate_hooks(self) -> None:
        if not self.current_registered_hooks:
            print("No hooks to deactivate")
            return
        self.cache_hooks()
        essential = self._filter_essential(self.current_registered_hooks)
        self.settings["hooks"] = essential
        save_json(SETTINGS_FILE, self.settings)
        self._set_last_action("deactivate")
        print("Hooks deactivated (essential hooks preserved)")

    def toggle_hooks(self) -> None:
        if self.last_action == "activate":
            self.deactivate_hooks()
        else:
            self.activate_hooks()

    def list_hooks(self) -> None:
        hooks = self.current_registered_hooks
        if not hooks:
            print("No hooks registered")
            return
        for event, entries in hooks.items():
            print(f"\n{event}:")
            for entry in entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "N/A")
                    timeout = hook.get("timeout", "default")
                    print(f"  - {cmd}  (timeout: {timeout})")

    def add_hook(self, event: str, command: str, timeout: int = 30) -> None:
        hooks = self.current_registered_hooks
        entry = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
        hooks.setdefault(event, []).append(entry)
        self.settings["hooks"] = hooks
        save_json(SETTINGS_FILE, self.settings)
        print(f"Hook added to {event}: {command}")

    def remove_hook(self, event: str, command: str) -> None:
        hooks = self.current_registered_hooks
        if event not in hooks:
            print(f"No hooks found for event: {event}")
            return
        original_count = len(hooks[event])
        hooks[event] = [
            entry
            for entry in hooks[event]
            if not any(h.get("command") == command for h in entry.get("hooks", []))
        ]
        if len(hooks[event]) == original_count:
            print(f"No hook matching command: {command}")
            return
        if not hooks[event]:
            del hooks[event]
        self.settings["hooks"] = hooks
        save_json(SETTINGS_FILE, self.settings)
        print(f"Hook removed from {event}: {command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Claude hooks")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("activate", help="Restore hooks from cache")
    sub.add_parser("deactivate", help="Cache current hooks and clear them")
    sub.add_parser("toggle", help="Toggle between activate/deactivate")
    sub.add_parser("list", help="Show all registered hooks")

    add_p = sub.add_parser("add", help="Add a hook to an event")
    add_p.add_argument(
        "event", help="Event type (e.g. PreToolUse, PostToolUse, UserPromptSubmit)"
    )
    add_p.add_argument("hook_command", help="Shell command to run")
    add_p.add_argument(
        "--timeout", type=int, default=30, help="Timeout in seconds (default: 30)"
    )

    rm_p = sub.add_parser("remove", help="Remove a hook by event and command")
    rm_p.add_argument("event", help="Event type")
    rm_p.add_argument("hook_command", help="Command string to match")

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    registry = HooksRegistry()

    match args.command:
        case "activate":
            registry.activate_hooks()
        case "deactivate":
            registry.deactivate_hooks()
        case "toggle":
            registry.toggle_hooks()
        case "list":
            registry.list_hooks()
        case "add":
            registry.add_hook(args.event, args.hook_command, args.timeout)
        case "remove":
            registry.remove_hook(args.event, args.hook_command)

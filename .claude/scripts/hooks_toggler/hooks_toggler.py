#!/usr/bin/env python3
"""Reactivate previously deactivated hooks from cache."""

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

    def register_security_hook(self) -> None:
        """Note this will overrides current hooks"""
        registry = {
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/security/security.py"',
                            "timeout": 30,
                        }
                    ]
                }
            ]
        }
        self.settings["hooks"] = registry
        save_json(SETTINGS_FILE, self.settings)

    def deactivate_hooks(self) -> None:
        if not self.current_registered_hooks:
            print("No hooks to deactivate")
            return
        self.cache_hooks()
        self.clear_hooks()
        self.register_security_hook()


if __name__ == "__main__":
    hooks_registry = HooksRegistry()
    hooks_registry.deactivate_hooks()

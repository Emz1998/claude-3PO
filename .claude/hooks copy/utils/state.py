import json
import sys
from pathlib import Path
from typing import Any, Literal
from filelock import FileLock
import os


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


class StateManager:
    """Sprint manager for workflow orchestration."""

    def __init__(self, state_path: Path):
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        self._state_path = state_path
        self._state: dict[str, Any] | None = None
        self._state_lock = FileLock(self._state_path.with_suffix(".lock"))
        self._check_file(state_path)

    def get_state_path(self) -> Path:
        """Get the state path.

        Returns:
            Path to the state.json file
        """
        return self._state_path

    def set_state_path(self, state_path: Path) -> None:
        """Set the state path.

        Args:
            state_path: Path to the state.json file
        """
        self._state_path = state_path
        self._check_file(state_path)

    # ----------------------------------------
    ## Load, save, and persist methods

    def _check_file(self, state_path: Path) -> bool:
        """Check if the state file exists.

        Returns:
            True if the state file exists, False otherwise
        """
        if state_path.exists():
            print(f"State file already exists: {state_path}")
            return True
        print(f"State file does not exist: {state_path}")
        print("Creating state file...")
        self._create_file()
        return False

    def _create_file(self) -> None:
        """Create the state file."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = {}
        self.save()

    def initialize(self, state: dict[str, Any] | None = None) -> None:
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        if state is None:
            state = {}

        self._state = state
        self.save()

    def reset(self, mode: Literal["hard", "soft"] = "soft") -> None:
        """Reset the state manager."""
        if mode == "hard":
            self._state = {}
            self.save()
        elif mode == "soft":
            self.save({})

    def load(self) -> dict[str, Any]:
        """Load state from file.

        Returns:
            State dictionary
        """
        with self._state_lock:
            state: dict[str, Any] = {}
            if self._state_path.exists():
                try:
                    state = json.loads(self._state_path.read_text())
                except json.JSONDecodeError:
                    self.save({})
                except (IOError, TypeError):
                    pass
            self._state = state
            return state

    ## Save methods

    def save(
        self,
        state: dict[str, Any] | None = None,
    ) -> None:
        """Save state to file.

        Args:
            state: State to save
        """

        with self._state_lock:
            if state is not None:
                self._state = state
            if self._state is None:
                return

            tmp = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._state, indent=2))
            os.replace(tmp, self._state_path)

    # ----------------------------------------

    ## Get, set, delete, reset methods

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state.

        Args:
            key: State key to retrieve
            default: Default value if key not found

        Returns:
            Value for key or default
        """
        if self._state is None:
            self.load()
        return (self._state or {}).get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state and save.

        Args:
            key: State key to set
            value: Value to set
        """
        if self._state is None:
            self.load()
        if self._state is None:
            self._state = {}
        self._state[key] = value
        self.save()

    def archive(self, archive_path: Path | None = None) -> None:
        """Archive the state file."""
        if archive_path is None:
            parent_dir = self._state_path.parent
            archive_path = parent_dir / "history.jsonl"

        append_text(archive_path, json.dumps(self._state) + "\n")

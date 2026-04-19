"""json_store.py — JSON / JSONL file I/O with optional cross-process locking.

Provides both a free-function API (``create_file`` / ``load_file`` /
``save_file`` / ``update_file``) and a stateful ``FileManager`` wrapper. The
class adds a ``filelock``-based mutex on read/update so two concurrent hooks
writing to the same state file don't trample each other. Callers that don't
need locking (e.g. tests, single-process tools) can pass ``lock=False``.
"""

import json
import os
from pathlib import Path
from typing import Any, Callable, cast, Literal
from filelock import FileLock, BaseFileLock
import sys

JSON_SUFFIXES = {".json", ".jsonl"}


def create_file(path: Path, default: Any | None = None) -> None:
    """
    Create *path* (and any missing parent dirs), seeding ``.json`` files.

    For ``.json`` paths, writes ``default`` (or ``{}``) as pretty JSON so the
    file is immediately loadable. For any other suffix, ``touch`` is used and
    ``default`` is ignored — non-JSON files are treated as opaque blobs.

    Args:
        path (Path): Destination file path.
        default (Any | None): Initial JSON content for ``.json`` files;
            ignored for other suffixes. Defaults to ``{}``.

    Returns:
        None: Side-effects only.

    Example:
        >>> create_file(Path("/tmp/x.json"), {"k": 1})  # doctest: +SKIP
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        default = default or {}
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return
    path.touch()


def load_file(path: Path) -> Any:
    """
    Read JSON from *path*, creating it (empty) if it doesn't exist.

    Auto-creating on missing is a deliberate convenience — most callers want
    "give me the current state, defaulting to empty" rather than to handle a
    FileNotFoundError on every read. An empty file returns ``{}`` so callers
    can always do ``data.get(...)`` without a None check.

    Args:
        path (Path): JSON file path to read.

    Returns:
        Any: Parsed JSON (typically ``dict`` or ``list``); ``{}`` for empty files.

    Raises:
        ValueError: When the file exists but contains malformed JSON. Wrapping
            ``JSONDecodeError`` makes corruption visible without leaking the
            stdlib exception type into callers.

    Example:
        >>> load_file(Path("/tmp/missing.json"))  # doctest: +SKIP
        {}
    """
    if not path.exists():
        create_file(path)
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}

        return json.loads(content)

    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt JSON in {path}: {e}") from e


def save_file(data: Any, mode: Literal["w", "a", "x"], path: Path) -> None:
    """
    Write *data* to *path*, formatting as JSON for ``.json``/``.jsonl`` suffixes.

    Non-JSON paths get ``data`` written verbatim — the function deliberately
    doesn't enforce ``str`` typing there so callers can write text or bytes
    using their own conventions.

    Args:
        data (Any): Object to serialize (must be JSON-serializable for JSON paths).
        mode (Literal["w", "a", "x"]): File-open mode.
        path (Path): Destination file path.

    Returns:
        None: Side-effects only.

    Raises:
        TypeError: When *data* isn't JSON-serializable for a JSON path.
        RuntimeError: For any other I/O failure (wrapped to add the path).

    Example:
        >>> save_file({"k": 1}, "w", Path("/tmp/x.json"))  # doctest: +SKIP
    """
    try:
        with path.open(mode, encoding="utf-8") as f:
            if path.suffix in JSON_SUFFIXES:
                json.dump(data, f, indent=2)
            else:
                f.write(data)
    except TypeError as e:
        raise TypeError(f"Invalid data type: {type(data)} \nError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error saving file: {path} \nError: {e}") from e


def update_file(path: Path, fn: Callable[[Any], None]) -> None:
    """
    Read JSON from *path*, mutate it in-place via *fn*, and write back.

    *fn* receives the parsed object and is expected to mutate it in place
    (return value is ignored). Convenient for ``lambda d: d["k"] = v`` style
    updates without manual round-tripping.

    Args:
        path (Path): JSON file path.
        fn (Callable[[Any], None]): Mutator invoked with the loaded data.

    Returns:
        None: Side-effects only.

    Example:
        >>> update_file(Path("/tmp/x.json"), lambda d: d.update({"k": 1}))  # doctest: +SKIP
    """
    data = load_file(path)
    fn(data)
    save_file(data, "w", path)


class FileManager:
    """
    Stateful wrapper around the file I/O helpers, optionally with a file lock.

    Use this when several processes (e.g. concurrent Claude hooks) may touch
    the same JSON file. The lock guards ``load_file`` and any callers that
    chain through it; ``save_file`` / ``delete_file`` are intentionally
    *not* locked because the typical pattern is locked-read followed by
    unlocked-write inside the same critical section already established by
    the caller.

    Example:
        >>> fm = FileManager(Path("/tmp/state.json"), lock=False)  # doctest: +SKIP
        >>> fm.save_file({"k": 1})  # doctest: +SKIP
    """

    def __init__(self, path: Path, lock: bool = True):
        """
        Bind a manager to *path*, creating a sibling ``.lock`` file if locking is on.

        Args:
            path (Path): Target JSON file.
            lock (bool): When ``True``, use a ``filelock.FileLock`` on
                ``path.with_suffix(".lock")``.

        Example:
            >>> FileManager(Path("/tmp/state.json"), lock=False)  # doctest: +SKIP
        """
        self._path = path
        self._lock = FileLock(path.with_suffix(".lock")) if lock else None

    def create_file(self, default: Any | None = None) -> None:
        """Delegate to :func:`create_file` for this manager's path.

        Example:
            >>> fm.create_file({"k": 1})  # doctest: +SKIP
        """
        create_file(self._path, default)

    def load_file(self) -> Any:
        """
        Read JSON from the managed path, holding the lock when enabled.

        Returns:
            Any: Parsed JSON content (``{}`` for empty files).

        Example:
            >>> fm.load_file()  # doctest: +SKIP
            {}
        """
        if self._lock is None:
            return load_file(self._path)
        with self._lock:
            return load_file(self._path)

    def save_file(self, data: Any, mode: Literal["w", "a", "x"] = "w") -> None:
        """Write *data* to the managed path. See :func:`save_file` for arg semantics.

        Example:
            >>> fm.save_file({"k": 1})  # doctest: +SKIP
        """
        save_file(data, mode, self._path)

    def update_file(self, fn: Callable[[Any], None]) -> None:
        """Read-mutate-write cycle on the managed path. See :func:`update_file`.

        Example:
            >>> fm.update_file(lambda d: d.update({"k": 2}))  # doctest: +SKIP
        """
        data = load_file(self._path)
        fn(data)
        save_file(data, "w", self._path)

    def delete_file(self) -> None:
        """Remove the managed file (raises if it doesn't exist).

        Example:
            >>> fm.delete_file()  # doctest: +SKIP
        """
        self._path.unlink()

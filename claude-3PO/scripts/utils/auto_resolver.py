#!/usr/bin/env python3
"""auto_resolver.py — watch ``state.json`` and run :func:`resolver.resolve` on every change.

The synchronous hooks already call ``resolve(config, state)`` after their
own mutations, but anything that edits ``state.json`` *outside* a hook
(manual edits, the migrate script, future auto-mutators) used to wait for
the next hook to advance the workflow. This watcher closes that gap by
firing the same ``resolve`` entry-point as soon as the file changes.

Standalone CLI; lives under ``utils/`` because there is no stdin hook —
it is started manually (or by a process manager) and runs in the
foreground until SIGINT.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from config import Config
from lib.state_store import StateStore
from utils.resolver import resolve


logger = logging.getLogger(__name__)


class AutoResolverHandler(FileSystemEventHandler):
    """Fire :func:`resolve` whenever the configured ``state.json`` is modified.

    The watchdog observer streams *every* event in the parent directory; the
    handler narrows them to the one file we care about so siblings (locks,
    migration leftovers, swap files) don't trigger spurious resolves.

    Example:
        >>> AutoResolverHandler(Path("/tmp/state.json"))  # doctest: +SKIP
        Return: <AutoResolverHandler>
    """

    def __init__(self, state_path: Path) -> None:
        """Bind the handler to a single ``state.json`` path.

        Args:
            state_path (Path): The watched state file (must already be
                resolved to absolute form by the caller).

        Returns:
            None: Constructor — stores *state_path* on ``self``.

        Example:
            >>> AutoResolverHandler(Path("/tmp/state.json"))  # doctest: +SKIP
            Return: <AutoResolverHandler>
        """
        super().__init__()
        # Snapshot the path so on_modified can do a cheap equality check.
        self.state_path = state_path

    def on_modified(self, event: FileSystemEvent) -> None:
        """Run :func:`resolve` when *event* targets the watched ``state.json``.

        Directory events and modifications to sibling files are ignored.
        Resolve errors are logged but do not crash the observer thread.

        Args:
            event (FileSystemEvent): Watchdog event describing the change.

        Returns:
            None: Side-effects only.

        SideEffect:
            Calls ``resolver.resolve(config, state)``; advances the workflow.

        Example:
            >>> handler.on_modified(event)  # doctest: +SKIP
            Return: None
            SideEffect:
                resolver.resolve fired for state.json
        """
        # Filter out directory ticks and unrelated files in the same dir.
        if event.is_directory or Path(event.src_path) != self.state_path:
            return
        self._invoke_resolve()

    def _invoke_resolve(self) -> None:
        """Build a fresh Config + StateStore and call :func:`resolve` once.

        Returns:
            None: Side-effects only.

        SideEffect:
            Logs a one-line summary; runs ``resolver.resolve``.

        Example:
            >>> handler._invoke_resolve()  # doctest: +SKIP
            Return: None
            SideEffect:
                resolver.resolve invoked; "auto_resolver: ..." log emitted
        """
        # Fresh objects per fire — the file's contents may have changed.
        config = Config()
        state = StateStore(self.state_path)
        try:
            resolve(config, state)
            logger.info("auto_resolver: resolve fired for %s", self.state_path)
        except Exception:
            # Never let a single resolve failure kill the watcher thread.
            logger.exception("auto_resolver: resolve raised for %s", self.state_path)


class AutoResolver:
    """Glue: own the watchdog Observer, the handler, and lifecycle management.

    Example:
        >>> AutoResolver(Path("/tmp/state.json"))  # doctest: +SKIP
        Return: <AutoResolver>
    """

    def __init__(self, state_path: Path) -> None:
        """Wire an Observer to *state_path*'s parent directory.

        Args:
            state_path (Path): The single-session state.json to watch.

        Returns:
            None: Constructor — sets ``self.handler`` and ``self.observer``.

        SideEffect:
            Schedules a watch on ``state_path.parent`` (recursive=False).

        Example:
            >>> AutoResolver(Path("/tmp/state.json"))  # doctest: +SKIP
            Return: <AutoResolver>
        """
        # Keep the absolute path so equality checks survive cwd changes.
        self.state_path = state_path.resolve()
        self.handler = AutoResolverHandler(self.state_path)
        self.observer = Observer()
        # Watch the parent dir; the handler filters down to state.json.
        self.observer.schedule(self.handler, str(self.state_path.parent), recursive=False)

    def start(self) -> None:
        """Start the observer thread.

        Returns:
            None: Side-effects only.

        SideEffect:
            Spawns the watchdog observer thread.

        Example:
            >>> resolver.start()  # doctest: +SKIP
            Return: None
            SideEffect:
                observer thread alive
        """
        self.observer.start()

    def stop(self) -> None:
        """Stop and join the observer thread.

        Returns:
            None: Side-effects only.

        SideEffect:
            Stops the observer; blocks until the thread joins.

        Example:
            >>> resolver.stop()  # doctest: +SKIP
            Return: None
            SideEffect:
                observer thread stopped + joined
        """
        self.observer.stop()
        self.observer.join()


def _resolve_state_path(arg: str | None) -> Path:
    """Resolve the CLI ``--state-path`` arg to an absolute :class:`Path`.

    Falls back to ``Config().default_state_json`` so the caller does not
    need to know the in-tree default.

    Args:
        arg (str | None): Raw ``--state-path`` argument (or None).

    Returns:
        Path: Absolute state.json path.

    Example:
        >>> _resolve_state_path(None)  # doctest: +SKIP
        Return: PosixPath('/.../scripts/state.json')
    """
    raw = arg or Config().default_state_json
    # Resolve relative paths against the scripts dir so callers can pass ".claude/state.json".
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = SCRIPTS_DIR / candidate
    return candidate.resolve()


def main() -> None:
    """CLI entry — start the watcher and block until SIGINT.

    Args (CLI):
        --state-path: Optional override for the watched state.json path.

    Returns:
        None: Runs in the foreground; returns when the observer is stopped.

    Example:
        >>> main()  # doctest: +SKIP
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Watch state.json and auto-resolve.")
    parser.add_argument("--state-path", default=None, help="Override state.json path")
    args = parser.parse_args()

    state_path = _resolve_state_path(args.state_path)
    auto = AutoResolver(state_path)
    auto.start()
    logger.info("auto_resolver: watching %s", state_path)

    # SIGINT-driven blocking loop; signal.pause() returns when SIGINT lands.
    signal.signal(signal.SIGINT, lambda *_: auto.stop())
    try:
        signal.pause()
    except KeyboardInterrupt:
        auto.stop()


if __name__ == "__main__":
    main()

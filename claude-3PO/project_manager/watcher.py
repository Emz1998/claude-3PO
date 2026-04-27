"""Watchdog-based watcher for ``project.json``.

On every modify event the watcher debounces for 500 ms (so editor save
bursts collapse into one cycle), then hashes the file; if the hash
matches the last one we processed the event is a self-write echo and
we skip it. Otherwise we call :func:`resolver.resolve` to apply the
status rules, save if anything changed, and always push the resulting
state to GitHub Projects via :class:`Syncer`. The net effect: any edit
to ``project.json`` — manual or programmatic — is reflected in GitHub
without a second CLI command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import signal
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .resolver import resolve
from .sync import Syncer


logger = logging.getLogger(__name__)

DEFAULT_DEBOUNCE_SECONDS = 0.5


class ProjectWatcherHandler(FileSystemEventHandler):
    """Filter events to the watched file and delegate to the owning watcher.

    Example:
        >>> ProjectWatcherHandler(Path("/tmp/p.json"), lambda: None)  # doctest: +SKIP
        Return: <ProjectWatcherHandler>
    """

    def __init__(self, backlog_path: Path, on_match) -> None:
        """Bind the handler to a single file path and a schedule-callback.

        Args:
            backlog_path (Path): Absolute path of the watched file.
            on_match (Callable[[], None]): Called for every modify event
                that targets ``backlog_path`` — typically the owning
                watcher's debounce-scheduler.

        Returns:
            None: Constructor.

        Example:
            >>> ProjectWatcherHandler(Path("/tmp/p.json"), lambda: None)  # doctest: +SKIP
            Return: <ProjectWatcherHandler>
        """
        super().__init__()
        # Snapshot the path so on_modified can do a cheap equality check
        # against every event streaming from the parent directory.
        self.backlog_path = backlog_path
        self.on_match = on_match

    def on_modified(self, event: FileSystemEvent) -> None:
        """Delegate to ``on_match`` when the modify event targets the backlog.

        Args:
            event (FileSystemEvent): Watchdog event.

        Returns:
            None: Side-effects only.

        SideEffect:
            Calls ``self.on_match()`` when the event matches.

        Example:
            >>> handler.on_modified(evt)  # doctest: +SKIP
            Return: None
        """
        # Drop directory ticks and modifications to sibling files.
        if event.is_directory or Path(event.src_path) != self.backlog_path:
            return
        self.on_match()


class ProjectWatcher:
    """Own the Observer, the handler, the debounce timer, and the last-hash.

    Example:
        >>> ProjectWatcher(Path("/tmp/p.json"))  # doctest: +SKIP
        Return: <ProjectWatcher>
    """

    def __init__(
        self,
        backlog_path: Path,
        *,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        syncer_kwargs: dict | None = None,
    ) -> None:
        """Wire the Observer to ``backlog_path``'s parent directory.

        Args:
            backlog_path (Path): Watched ``project.json``.
            debounce_seconds (float): Window that collapses editor save
                bursts into one resolve+sync cycle.
            syncer_kwargs (dict | None): Extra kwargs forwarded to
                :class:`Syncer` (``repo``, ``project``, ``owner``).

        Returns:
            None: Constructor.

        Example:
            >>> ProjectWatcher(Path("/tmp/p.json"))  # doctest: +SKIP
            Return: <ProjectWatcher>
        """
        # Store absolute path so equality checks survive cwd changes.
        self.backlog_path = Path(backlog_path).resolve()
        self.debounce_seconds = debounce_seconds
        self._syncer_kwargs = syncer_kwargs or {}
        self._last_processed_hash: str | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        # Separate lock guards against reentrant process_once: sync writes
        # issue_numbers back to the file mid-cycle, which fires watchdog →
        # another timer → another process_once. Two concurrent sync runs
        # race on GitHub (duplicate issue creation, conflicting field writes).
        self._process_lock = threading.Lock()
        self.handler = ProjectWatcherHandler(self.backlog_path, self._schedule_process)
        self.observer = Observer()
        self.observer.schedule(
            self.handler, str(self.backlog_path.parent), recursive=False
        )

    def start(self) -> None:
        """Start the observer thread.

        Returns:
            None: Side-effects only.

        SideEffect:
            Spawns the watchdog observer thread.

        Example:
            >>> pw.start()  # doctest: +SKIP
            Return: None
            SideEffect:
                observer thread alive
        """
        self.observer.start()

    def stop(self) -> None:
        """Stop the observer and cancel any pending debounce timer.

        Returns:
            None: Side-effects only.

        SideEffect:
            Stops the observer; cancels the pending timer; joins threads.

        Example:
            >>> pw.stop()  # doctest: +SKIP
            Return: None
            SideEffect:
                observer stopped, timer cancelled
        """
        # Cancel any in-flight debounce so we don't fire one last cycle
        # after the user asked to shut down.
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
        self.observer.stop()
        self.observer.join()

    def process_once(self) -> None:
        """Run one full cycle: hash-check → resolve → save → sync.

        Reentrant calls (a second timer firing mid-sync) return immediately
        instead of racing the in-flight cycle. The hash-dedup at the end of
        the running cycle will cover the skipped event.

        Returns:
            None: Side-effects only.

        SideEffect:
            May mutate ``project.json``; calls ``Syncer.run("sync")``;
            updates ``self._last_processed_hash``.

        Example:
            >>> pw.process_once()  # doctest: +SKIP
            Return: None
        """
        # Non-blocking acquire: drop reentrant calls instead of queuing them.
        if not self._process_lock.acquire(blocking=False):
            return
        try:
            self._run_cycle()
        finally:
            self._process_lock.release()

    def _run_cycle(self) -> None:
        """Body of :meth:`process_once`; runs under ``_process_lock``."""
        # Hash-based dedup blocks the watcher's own writeback from looping.
        current_hash = self._hash_file()
        if current_hash is None or current_hash == self._last_processed_hash:
            return
        self._resolve_and_save()
        self._safe_sync()
        # Record the post-processing hash so the next on_modified echo
        # (caused by our own save) is recognised and skipped.
        self._last_processed_hash = self._hash_file()

    def _resolve_and_save(self) -> None:
        """Load the backlog, run :func:`resolve`, write back if it changed.

        Returns:
            None: Side-effects only.

        SideEffect:
            Writes to ``self.backlog_path`` when resolve mutated the backlog.

        Example:
            >>> pw._resolve_and_save()  # doctest: +SKIP
            Return: None
        """
        backlog = json.loads(self.backlog_path.read_text(encoding="utf-8"))
        # resolve() returns True iff at least one rule fired.
        if resolve(backlog):
            self.backlog_path.write_text(
                json.dumps(backlog, indent=2) + "\n", encoding="utf-8"
            )
            logger.info("watcher: resolver mutated %s", self.backlog_path)

    def _safe_sync(self) -> None:
        """Invoke ``Syncer.run("sync")``; log and swallow any failure.

        Returns:
            None: Side-effects only.

        SideEffect:
            Calls out to the ``gh`` CLI via :class:`Syncer`.

        Example:
            >>> pw._safe_sync()  # doctest: +SKIP
            Return: None
        """
        try:
            syncer = Syncer(backlog_path=self.backlog_path, **self._syncer_kwargs)
            syncer.run("sync")
        except Exception:
            # Never let a sync failure kill the long-running watcher.
            logger.exception("watcher: sync failed for %s", self.backlog_path)

    def _hash_file(self) -> str | None:
        """Return the SHA-256 of the watched file, or ``None`` if missing.

        Returns:
            str | None: Hex digest, or None when the file doesn't exist.

        Example:
            >>> pw._hash_file()  # doctest: +SKIP
            Return: 'abc123...'
        """
        # File may briefly not exist mid-save (atomic-rename editors).
        if not self.backlog_path.exists():
            return None
        return hashlib.sha256(self.backlog_path.read_bytes()).hexdigest()

    def _schedule_process(self) -> None:
        """Start/reset the debounce timer that fires :meth:`process_once`.

        Returns:
            None: Side-effects only.

        SideEffect:
            Cancels any pending ``threading.Timer`` and starts a fresh one.

        Example:
            >>> pw._schedule_process()  # doctest: +SKIP
            Return: None
        """
        # Coalesce bursts: a new event while a timer is pending resets it.
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self.process_once)
            self._timer.daemon = True
            self._timer.start()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_syncer_kwargs(args: argparse.Namespace) -> dict:
    """Extract Syncer override flags from parsed args, dropping Nones.

    Args:
        args (argparse.Namespace): Parsed CLI args.

    Returns:
        dict: Sparse kwargs ready to pass to :class:`Syncer`.

    Example:
        >>> _build_syncer_kwargs(ns)  # doctest: +SKIP
        Return: {'repo': 'o/r'}
    """
    raw = {"repo": args.repo, "project": args.project, "owner": args.owner}
    return {k: v for k, v in raw.items() if v is not None}


def _resolve_backlog_path(arg: str | None) -> Path:
    """Return the absolute path to the backlog, falling back to the default.

    Args:
        arg (str | None): ``--backlog-path`` CLI argument.

    Returns:
        Path: Absolute backlog path.

    Example:
        >>> _resolve_backlog_path(None)  # doctest: +SKIP
        Return: PosixPath('/.../project.json')
    """
    from .config import DATA_PATHS

    raw = arg or DATA_PATHS["backlog"]
    return Path(raw).resolve()


def main_from_args(args: argparse.Namespace) -> int:
    """Shared entry-point for both ``python -m ... watcher`` and the CLI.

    Args:
        args (argparse.Namespace): Parsed CLI args with ``backlog_path``,
            ``repo``, ``project``, ``owner``.

    Returns:
        int: Process exit code (0 on clean shutdown).

    SideEffect:
        Starts the watcher; blocks until SIGINT.

    Example:
        >>> main_from_args(ns)  # doctest: +SKIP
        Return: 0
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    pw = ProjectWatcher(
        _resolve_backlog_path(args.backlog_path),
        syncer_kwargs=_build_syncer_kwargs(args),
    )
    pw.start()
    logger.info("watcher: watching %s", pw.backlog_path)
    # Converge any drift that accrued while the watcher was off: a
    # `project.json` edited out-of-band (or a prior sync that crashed
    # mid-cycle) would otherwise stay unpushed until the next edit.
    # The observer is already running, so a real save during this sync
    # is queued, not lost.
    logger.info("watcher: running initial sync")
    pw.process_once()
    # SIGINT-driven blocking loop mirrors auto_resolver.main.
    signal.signal(signal.SIGINT, lambda *_: pw.stop())
    try:
        signal.pause()
    except KeyboardInterrupt:
        pw.stop()
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the standalone CLI parser (used when running this module directly).

    Returns:
        argparse.ArgumentParser: Configured parser.

    Example:
        >>> _build_arg_parser().parse_args([])  # doctest: +SKIP
        Return: Namespace(backlog_path=None, repo=None, project=None, owner=None)
    """
    ap = argparse.ArgumentParser(description="Watch project.json and auto-resolve+sync.")
    ap.add_argument("--backlog-path", default=None, help="Override project.json path")
    ap.add_argument("--repo", default=None, help="Override Syncer repo")
    ap.add_argument("--project", type=int, default=None, help="Override Syncer project")
    ap.add_argument("--owner", default=None, help="Override Syncer owner")
    return ap


def main() -> int:
    """CLI entry — parse args and block until SIGINT.

    Returns:
        int: Process exit code.

    Example:
        >>> main()  # doctest: +SKIP
    """
    return main_from_args(_build_arg_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

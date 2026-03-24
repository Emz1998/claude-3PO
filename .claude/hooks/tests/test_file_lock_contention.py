#!/usr/bin/env python3
"""
Multi-process contention tests for .claude/hooks/file_lock/file_lock.py

Covers the failure modes that matter most for SoftFileLock:
  1. Contention   — process B waits until process A releases
  2. Timeout      — process B gives up after timeout expires
  3. Stale lock   — holder crashes without releasing; waiter behavior observed
  4. Data integrity — shared counter stays correct under concurrent writes
  5. Stress       — repeated contention runs expose probabilistic races
"""

import json
import multiprocessing
import os
import sys
import time
from pathlib import Path

import pytest
from filelock import SoftFileLock, Timeout


# ---------------------------------------------------------------------------
# Helpers shared across worker functions
# ---------------------------------------------------------------------------

def _acquire_hold_release(lock_path: str, hold_seconds: float, out_path: str) -> None:
    """Worker: acquire the lock, log timing, hold, then release."""
    lock = SoftFileLock(lock_path, timeout=10)
    start = time.monotonic()
    with lock:
        waited = time.monotonic() - start
        with open(out_path, "a") as f:
            f.write(json.dumps({"waited": round(waited, 3), "hold": hold_seconds}) + "\n")
        time.sleep(hold_seconds)


def _acquire_with_timeout(lock_path: str, timeout: float, result_path: str) -> None:
    """Worker: try to acquire with a short timeout; record 'acquired' or 'timeout'."""
    try:
        with SoftFileLock(lock_path, timeout=timeout):
            Path(result_path).write_text("acquired")
    except Timeout:
        Path(result_path).write_text("timeout")


def _crash_after_acquire(lock_path: str) -> None:
    """Worker: acquire then hard-crash (no cleanup)."""
    lock = SoftFileLock(lock_path, timeout=5)
    lock.acquire()
    os._exit(1)  # simulate process crash — skips all cleanup


def _increment_counter(lock_path: str, data_path: str, n: int) -> None:
    """Worker: increment a JSON counter n times under the lock."""
    lock = SoftFileLock(lock_path, timeout=20)
    for _ in range(n):
        with lock:
            data = json.loads(Path(data_path).read_text())
            value = data["count"]
            time.sleep(0.005)  # widen the contention window
            data["count"] = value + 1
            Path(data_path).write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# 1. Contention — B waits for A
# ---------------------------------------------------------------------------

class TestContention:
    def test_second_process_waits(self, tmp_path):
        """Process B must not enter the critical section until A releases."""
        lock_path = str(tmp_path / "contention.lock")
        out_path = str(tmp_path / "events.jsonl")
        Path(out_path).write_text("")

        p_a = multiprocessing.Process(target=_acquire_hold_release, args=(lock_path, 1.5, out_path))
        p_b = multiprocessing.Process(target=_acquire_hold_release, args=(lock_path, 0.1, out_path))

        p_a.start()
        time.sleep(0.1)  # let A likely acquire first
        p_b.start()

        p_a.join(timeout=10)
        p_b.join(timeout=10)

        events = [json.loads(line) for line in Path(out_path).read_text().splitlines() if line]
        assert len(events) == 2, "Both processes must complete"

        # B must have waited at least as long as A held (1.5s), minus startup slack
        waited_values = sorted(e["waited"] for e in events)
        assert waited_values[1] >= 1.0, (
            f"Second acquirer waited only {waited_values[1]:.2f}s — "
            "likely ran concurrently instead of waiting"
        )

    def test_only_one_inside_at_a_time(self, tmp_path):
        """Active ranges must never overlap: no two processes inside simultaneously."""
        lock_path = str(tmp_path / "overlap.lock")
        timeline_path = str(tmp_path / "timeline.jsonl")
        Path(timeline_path).write_text("")

        def worker(name: str) -> None:
            lock = SoftFileLock(lock_path, timeout=15)
            with lock:
                enter = time.monotonic()
                time.sleep(0.2)
                exit_ = time.monotonic()
                with open(timeline_path, "a") as f:
                    f.write(json.dumps({"name": name, "enter": enter, "exit": exit_}) + "\n")

        procs = [multiprocessing.Process(target=worker, args=(str(i),)) for i in range(4)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=20)

        intervals = [json.loads(l) for l in Path(timeline_path).read_text().splitlines() if l]
        assert len(intervals) == 4

        # Check no two intervals overlap
        for i, a in enumerate(intervals):
            for b in intervals[i + 1:]:
                overlap = a["enter"] < b["exit"] and b["enter"] < a["exit"]
                assert not overlap, (
                    f"Processes {a['name']} and {b['name']} were inside simultaneously"
                )


# ---------------------------------------------------------------------------
# 2. Timeout — waiter gives up
# ---------------------------------------------------------------------------

class TestTimeout:
    def test_waiter_times_out_while_holder_blocks(self, tmp_path):
        """A process waiting longer than its timeout must receive Timeout, not hang."""
        lock_path = str(tmp_path / "timeout.lock")
        result_path = str(tmp_path / "result.txt")

        holder = multiprocessing.Process(
            target=_acquire_hold_release,
            args=(lock_path, 3.0, str(tmp_path / "holder.jsonl")),
        )
        waiter = multiprocessing.Process(
            target=_acquire_with_timeout,
            args=(lock_path, 1.0, result_path),
        )

        Path(tmp_path / "holder.jsonl").write_text("")
        holder.start()
        time.sleep(0.2)  # let holder grab the lock first
        waiter.start()

        holder.join(timeout=10)
        waiter.join(timeout=5)

        assert Path(result_path).read_text() == "timeout", (
            "Waiter should have timed out, but it acquired the lock"
        )

    def test_waiter_acquires_after_holder_releases(self, tmp_path):
        """When holder releases before timeout, waiter must succeed."""
        lock_path = str(tmp_path / "short_hold.lock")
        result_path = str(tmp_path / "result.txt")

        holder = multiprocessing.Process(
            target=_acquire_hold_release,
            args=(lock_path, 0.3, str(tmp_path / "holder.jsonl")),
        )
        waiter = multiprocessing.Process(
            target=_acquire_with_timeout,
            args=(lock_path, 5.0, result_path),
        )

        Path(tmp_path / "holder.jsonl").write_text("")
        holder.start()
        time.sleep(0.1)
        waiter.start()

        holder.join(timeout=5)
        waiter.join(timeout=10)

        assert Path(result_path).read_text() == "acquired"


# ---------------------------------------------------------------------------
# 3. Stale lock — holder crashes without cleanup
# ---------------------------------------------------------------------------

class TestStaleLock:
    def test_lock_file_remains_after_crash(self, tmp_path):
        """SoftFileLock does NOT auto-clean on crash; the file must still exist."""
        lock_path = tmp_path / "stale.lock"

        p = multiprocessing.Process(target=_crash_after_acquire, args=(str(lock_path),))
        p.start()
        p.join(timeout=5)

        assert lock_path.exists(), (
            "Lock file should remain after crash — stale locks require explicit cleanup"
        )

    def test_waiter_blocks_on_stale_lock(self, tmp_path):
        """A stale lock blocks subsequent acquirers until it is manually removed."""
        lock_path = tmp_path / "stale_block.lock"
        result_path = str(tmp_path / "result.txt")

        crash_proc = multiprocessing.Process(target=_crash_after_acquire, args=(str(lock_path),))
        crash_proc.start()
        crash_proc.join(timeout=5)

        # Stale lock is now on disk; waiter with short timeout must time out
        waiter = multiprocessing.Process(
            target=_acquire_with_timeout,
            args=(str(lock_path), 1.0, result_path),
        )
        waiter.start()
        waiter.join(timeout=5)

        assert Path(result_path).read_text() == "timeout", (
            "Waiter should have timed out on the stale lock"
        )

    def test_recovery_after_stale_lock_deleted(self, tmp_path):
        """After manually deleting a stale lock, a new acquirer must succeed."""
        lock_path = tmp_path / "stale_recover.lock"
        result_path = str(tmp_path / "result.txt")

        crash_proc = multiprocessing.Process(target=_crash_after_acquire, args=(str(lock_path),))
        crash_proc.start()
        crash_proc.join(timeout=5)

        assert lock_path.exists()
        lock_path.unlink()  # manual recovery

        waiter = multiprocessing.Process(
            target=_acquire_with_timeout,
            args=(str(lock_path), 2.0, result_path),
        )
        waiter.start()
        waiter.join(timeout=5)

        assert Path(result_path).read_text() == "acquired", (
            "After stale lock is deleted, acquisition must succeed"
        )


# ---------------------------------------------------------------------------
# 4. Data integrity — shared counter stays correct under contention
# ---------------------------------------------------------------------------

class TestDataIntegrity:
    def test_counter_correct_under_contention(self, tmp_path):
        """Final counter value must equal total increments across all workers."""
        lock_path = str(tmp_path / "counter.lock")
        data_path = str(tmp_path / "counter.json")
        n_workers = 4
        n_increments = 30  # per worker

        Path(data_path).write_text(json.dumps({"count": 0}))

        workers = [
            multiprocessing.Process(
                target=_increment_counter,
                args=(lock_path, data_path, n_increments),
            )
            for _ in range(n_workers)
        ]

        for p in workers:
            p.start()
        for p in workers:
            p.join(timeout=60)

        result = json.loads(Path(data_path).read_text())
        expected = n_workers * n_increments
        assert result["count"] == expected, (
            f"Expected {expected}, got {result['count']} — "
            "lock did not prevent concurrent writes"
        )


# ---------------------------------------------------------------------------
# 5. Stress — repeated runs expose probabilistic races
# ---------------------------------------------------------------------------

class TestStress:
    @pytest.mark.parametrize("run", range(5))
    def test_counter_correct_repeated(self, run, tmp_path):
        """Counter integrity must hold across repeated independent runs."""
        lock_path = str(tmp_path / "stress.lock")
        data_path = str(tmp_path / "stress.json")
        n_workers = 3
        n_increments = 20

        Path(data_path).write_text(json.dumps({"count": 0}))

        workers = [
            multiprocessing.Process(
                target=_increment_counter,
                args=(lock_path, data_path, n_increments),
            )
            for _ in range(n_workers)
        ]

        for p in workers:
            p.start()
        for p in workers:
            p.join(timeout=60)

        result = json.loads(Path(data_path).read_text())
        expected = n_workers * n_increments
        assert result["count"] == expected, (
            f"Run {run}: expected {expected}, got {result['count']}"
        )

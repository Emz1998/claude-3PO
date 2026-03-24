"""End-to-end tests for workflow/review/review.py

Runs main() as a subprocess — exactly as Claude Code's hook runner does —
piping a JSON hook payload to stdin and asserting on exit codes and
report files written to disk.

The real `claude` CLI is replaced by a tiny fake script placed earlier in PATH.
Session state is written to the real sessions directory using unique IDs,
and cleaned up after each test.
"""

import json
import os
import sys
import subprocess
import uuid
from pathlib import Path

import pytest

REVIEW_SCRIPT = Path(__file__).resolve().parents[1] / "review" / "review.py"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SESSIONS_DIR = PROJECT_ROOT / ".claude" / "sessions"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_report(files_to_revise: list[str]) -> str:
    files_yaml = "\n".join(f"  - {f}" for f in files_to_revise)
    return (
        f"---\nconfidence_score: 85\nquality_score: 80\n"
        f"files_to_revise:\n{files_yaml}\n---\n\nLooks good."
    )


def _make_fake_claude(bin_dir: Path, responses: list[str]) -> None:
    """Write a fake 'claude' that returns responses in order (last one repeated)."""
    counter = bin_dir / "_call_count"
    counter.write_text("0")
    script = bin_dir / "claude"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"responses = {json.dumps(responses)}\n"
        f"counter = r'{counter}'\n"
        "n = int(open(counter).read())\n"
        "open(counter, 'w').write(str(n + 1))\n"
        "text = responses[min(n, len(responses) - 1)]\n"
        f'print(json.dumps({{"session_id": f"claude-sid-{{n}}", "result": text}}))\n'
    )
    script.chmod(0o755)


def _make_session_state(session_id: str, workflow_active: bool = True) -> Path:
    state_path = SESSIONS_DIR / f"session_{session_id}" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"workflow_active": workflow_active}))
    return state_path


def _run_hook(payload: dict, bin_dir: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}
    return subprocess.run(
        [sys.executable, str(REVIEW_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )


def _unique_session_id() -> str:
    return f"e2e-test-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session_id():
    sid = _unique_session_id()
    yield sid
    # Cleanup: remove the session directory created during the test
    session_dir = SESSIONS_DIR / f"session_{sid}"
    if session_dir.exists():
        import shutil
        shutil.rmtree(session_dir)


@pytest.fixture
def fake_claude_bin(tmp_path):
    """Returns a factory: call with a list of response strings."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    def factory(responses: list[str]):
        _make_fake_claude(bin_dir, responses)
        return bin_dir

    return factory


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestReviewHappyPath:
    def test_report_file_written(self, session_id, fake_claude_bin, tmp_path):
        """Valid session + valid claude response → report file written at expected path."""
        src = tmp_path / "app.py"
        src.touch()

        _make_session_state(session_id)
        bin_dir = fake_claude_bin([_valid_report([str(src)])])

        payload = {
            "session_id": session_id,
            "tool_input": {"file_path": str(src)},
        }

        result = _run_hook(payload, bin_dir)

        assert result.returncode == 0, result.stderr
        report = SESSIONS_DIR / f"session_{session_id}" / "review" / "code-review.md"
        assert report.exists(), f"Expected report at {report}"
        assert "confidence_score" in report.read_text()

    def test_report_contains_valid_frontmatter(self, session_id, fake_claude_bin, tmp_path):
        """The written report must include all required frontmatter fields."""
        src = tmp_path / "service.ts"
        src.touch()

        _make_session_state(session_id)
        bin_dir = fake_claude_bin([_valid_report([str(src)])])

        _run_hook(
            {"session_id": session_id, "tool_input": {"file_path": str(src)}},
            bin_dir,
        )

        report = SESSIONS_DIR / f"session_{session_id}" / "review" / "code-review.md"
        text = report.read_text()
        assert "confidence_score" in text
        assert "quality_score" in text
        assert "files_to_revise" in text

    def test_plan_file_writes_plan_review_report(self, session_id, fake_claude_bin, tmp_path):
        """Files under a 'plans' path must produce a plan-review report."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "my-plan.md"
        plan_file.touch()

        _make_session_state(session_id)
        bin_dir = fake_claude_bin([_valid_report([str(plan_file)])])

        _run_hook(
            {"session_id": session_id, "tool_input": {"file_path": str(plan_file)}},
            bin_dir,
        )

        report = SESSIONS_DIR / f"session_{session_id}" / "review" / "plan-review.md"
        assert report.exists(), f"Expected plan-review report at {report}"


# ---------------------------------------------------------------------------
# Workflow inactive
# ---------------------------------------------------------------------------


class TestWorkflowInactive:
    def test_exits_silently_when_workflow_inactive(self, session_id, fake_claude_bin, tmp_path):
        """workflow_active=False → hook exits 0 without invoking claude or writing anything."""
        src = tmp_path / "app.py"
        src.touch()

        _make_session_state(session_id, workflow_active=False)
        bin_dir = fake_claude_bin(["this should never be called"])

        result = _run_hook(
            {"session_id": session_id, "tool_input": {"file_path": str(src)}},
            bin_dir,
        )

        assert result.returncode == 0
        review_dir = SESSIONS_DIR / f"session_{session_id}" / "review"
        assert not review_dir.exists()


# ---------------------------------------------------------------------------
# Missing / invalid input
# ---------------------------------------------------------------------------


class TestInvalidInput:
    def test_missing_session_id_raises(self, fake_claude_bin):
        """Payload without session_id must cause a non-zero exit."""
        bin_dir = fake_claude_bin(["irrelevant"])
        result = _run_hook({"tool_input": {"file_path": "/src/app.py"}}, bin_dir)
        assert result.returncode != 0

    def test_empty_stdin_exits_nonzero(self, tmp_path):
        """Malformed (empty) stdin must exit non-zero."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        result = subprocess.run(
            [sys.executable, str(REVIEW_SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------


class TestRetryBehaviour:
    def test_retries_on_missing_frontmatter(self, session_id, fake_claude_bin, tmp_path):
        """First response missing frontmatter triggers a retry; second valid response is used."""
        src = tmp_path / "app.py"
        src.touch()

        _make_session_state(session_id)
        bin_dir = fake_claude_bin(
            ["No frontmatter here.", _valid_report([str(src)])]
        )

        result = _run_hook(
            {"session_id": session_id, "tool_input": {"file_path": str(src)}},
            bin_dir,
        )

        assert result.returncode == 0, result.stderr
        report = SESSIONS_DIR / f"session_{session_id}" / "review" / "code-review.md"
        assert report.exists()

    def test_exceeding_max_retries_exits_nonzero(self, session_id, fake_claude_bin, tmp_path):
        """Persistently invalid responses must exhaust retries and exit non-zero."""
        src = tmp_path / "app.py"
        src.touch()

        _make_session_state(session_id)
        # Always return a response with no frontmatter
        bin_dir = fake_claude_bin(["No frontmatter, ever."])

        result = _run_hook(
            {"session_id": session_id, "tool_input": {"file_path": str(src)}},
            bin_dir,
        )

        assert result.returncode != 0

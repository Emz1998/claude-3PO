"""Tests for utils/initializer.py — arg parsing and state initialization."""

import json
import pytest
from pathlib import Path

from utils.initializer import (
    parse_skip,
    parse_story_id,
    parse_instructions,
    parse_frontmatter,
    archive_plan,
    build_initial_state,
    initialize,
)

try:
    from utils.initializer import archive_contracts
except ImportError:
    archive_contracts = None
from config import Config


# ═══════════════════════════════════════════════════════════════════
# parse_skip
# ═══════════════════════════════════════════════════════════════════


class TestParseSkip:
    def test_no_flags(self):
        assert parse_skip("build a login form") == []

    def test_skip_explore(self):
        assert parse_skip("--skip-explore build a login form") == ["explore"]

    def test_skip_research(self):
        assert parse_skip("--skip-research build a login form") == ["research"]

    def test_skip_all(self):
        assert parse_skip("--skip-all build a login form") == ["explore", "research"]

    def test_skip_explore_and_research(self):
        result = parse_skip("--skip-explore --skip-research build")
        assert result == ["explore", "research"]

    def test_empty_args(self):
        assert parse_skip("") == []


# ═══════════════════════════════════════════════════════════════════
# parse_story_id
# ═══════════════════════════════════════════════════════════════════


class TestParseStoryId:
    def test_extracts_story_id(self):
        assert parse_story_id("SK-001 build a login form") == "SK-001"

    def test_extracts_story_id_mid_string(self):
        assert parse_story_id("--tdd FEAT-42 build a form") == "FEAT-42"

    def test_no_story_id(self):
        assert parse_story_id("build a login form") is None

    def test_empty_args(self):
        assert parse_story_id("") is None

    def test_multiple_ids_returns_first(self):
        assert parse_story_id("SK-001 BUG-002") == "SK-001"


# ═══════════════════════════════════════════════════════════════════
# parse_instructions
# ═══════════════════════════════════════════════════════════════════


class TestParseInstructions:
    def test_strips_flags(self):
        result = parse_instructions("--tdd --skip-all build a login form")
        assert result == "build a login form"

    def test_strips_story_id(self):
        result = parse_instructions("SK-001 build a login form")
        assert result == "build a login form"

    def test_strips_all(self):
        result = parse_instructions("--tdd --skip-explore SK-001 build a login form")
        assert result == "build a login form"

    def test_no_flags_no_id(self):
        result = parse_instructions("build a login form")
        assert result == "build a login form"

    def test_only_flags(self):
        result = parse_instructions("--tdd --skip-all")
        assert result == ""

    def test_empty(self):
        assert parse_instructions("") == ""


# ═══════════════════════════════════════════════════════════════════
# build_initial_state
# ═══════════════════════════════════════════════════════════════════


class TestBuildInitialState:
    def test_default_state(self):
        state = build_initial_state("implement", "sess-1", "build a form")
        assert state["session_id"] == "sess-1"
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "implement"
        assert state["tdd"] is False
        assert state["story_id"] is None
        assert state["skip"] == []
        assert state["instructions"] == "build a form"
        assert state["phases"] == []

    def test_tdd_flag(self):
        state = build_initial_state("implement", "sess-1", "--tdd build a form")
        assert state["tdd"] is True

    def test_skip_all(self):
        state = build_initial_state("implement", "sess-1", "--skip-all build a form")
        assert state["phases"] == []
        assert state["skip"] == ["explore", "research"]

    def test_skip_explore_only(self):
        state = build_initial_state("implement", "sess-1", "--skip-explore build")
        assert state["phases"] == []

    def test_story_id_extracted(self):
        state = build_initial_state("implement", "sess-1", "SK-001 build a form")
        assert state["story_id"] == "SK-001"

    def test_all_schema_keys_present(self):
        state = build_initial_state("implement", "sess-1", "")
        expected_keys = {
            "session_id", "workflow_active", "workflow_type", "phases",
            "tdd", "story_id", "skip", "instructions",
            "agents", "plan", "tasks", "dependencies", "contracts",
            "tests", "code_files_to_write",
            "code_files", "quality_check_result", "pr", "ci-check",
            "report_written",
        }
        assert set(state.keys()) == expected_keys

    def test_nested_defaults(self):
        state = build_initial_state("implement", "sess-1", "")
        assert state["plan"]["written"] is False
        assert state["plan"]["reviews"] == []
        assert state["tests"]["executed"] is False
        assert state["code_files"]["file_paths"] == []
        assert state["pr"]["status"] == "pending"
        assert state["ci-check"]["status"] == "pending"
        assert state["report_written"] is False


# ═══════════════════════════════════════════════════════════════════
# initialize (integration)
# ═══════════════════════════════════════════════════════════════════


class TestInitialize:
    def test_writes_state_file(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        state_path.write_text("")
        initialize("implement", "sess-1", "--tdd SK-001 build a form", state_path)

        # Read JSONL — find the session line
        content = state_path.read_text().strip()
        state = json.loads(content.splitlines()[0])
        assert state["session_id"] == "sess-1"
        assert state["workflow_active"] is True
        assert state["tdd"] is True
        assert state["story_id"] == "SK-001"
        assert state["instructions"] == "build a form"


# ═══════════════════════════════════════════════════════════════════
# parse_frontmatter
# ═══════════════════════════════════════════════════════════════════


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nsession_id: abc-123\ndate: 2026-04-11\n---\n# Plan"
        fm = parse_frontmatter(content)
        assert fm["session_id"] == "abc-123"
        assert fm["date"] == "2026-04-11"

    def test_no_frontmatter(self):
        content = "# Plan\nSome content"
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_incomplete_frontmatter(self):
        content = "---\nsession_id: abc-123\n"
        fm = parse_frontmatter(content)
        assert fm == {}


# ═══════════════════════════════════════════════════════════════════
# archive_plan
# ═══════════════════════════════════════════════════════════════════


class TestArchivePlan:
    def test_archives_existing_plan(self, tmp_path: Path, monkeypatch):
        plan_dir = tmp_path / ".claude" / "plans"
        plan_dir.mkdir(parents=True)
        plan_path = plan_dir / "latest-plan.md"
        plan_path.write_text("---\nsession_id: old-sess\n---\n# Old Plan")

        archive_dir = plan_dir / "archive"

        config = Config()
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(plan_path)))
        monkeypatch.setattr(type(config), "plan_archive_dir", property(lambda self: str(archive_dir)))

        archive_plan(config)

        assert not plan_path.exists()
        archived = list(archive_dir.glob("plan_*_old-sess.md"))
        assert len(archived) == 1
        assert "# Old Plan" in archived[0].read_text()

    def test_no_plan_file_does_nothing(self, tmp_path: Path, monkeypatch):
        config = Config()
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(tmp_path / "nonexistent.md")))

        archive_plan(config)  # should not raise

    def test_plan_without_frontmatter_uses_unknown(self, tmp_path: Path, monkeypatch):
        plan_path = tmp_path / "latest-plan.md"
        plan_path.write_text("# Plan with no frontmatter")

        archive_dir = tmp_path / "archive"

        config = Config()
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(plan_path)))
        monkeypatch.setattr(type(config), "plan_archive_dir", property(lambda self: str(archive_dir)))

        archive_plan(config)

        assert not plan_path.exists()
        archived = list(archive_dir.glob("plan_*_unknown.md"))
        assert len(archived) == 1

    def test_reinitializes_existing_state(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        old_line = json.dumps({"session_id": "old", "workflow_active": False}, separators=(",", ":"))
        state_path.write_text(old_line + "\n")
        initialize("implement", "new-sess", "build", state_path)

        # The new session should be present
        content = state_path.read_text().strip()
        lines = content.splitlines()
        # Find the new-sess line
        new_state = None
        for line in lines:
            entry = json.loads(line)
            if entry.get("session_id") == "new-sess":
                new_state = entry
                break
        assert new_state is not None
        assert new_state["workflow_active"] is True


# ═══════════════════════════════════════════════════════════════════
# Initial state — dependencies + contracts fields
# ═══════════════════════════════════════════════════════════════════


class TestBuildInitialStateDepsContracts:
    def test_has_dependencies_field(self):
        state = build_initial_state("implement", "sess-1", "build a form")
        assert "dependencies" in state
        assert state["dependencies"]["packages"] == []
        assert state["dependencies"]["installed"] is False

    def test_has_contracts_field(self):
        state = build_initial_state("implement", "sess-1", "build a form")
        assert "contracts" in state
        assert state["contracts"]["file_path"] is None
        assert state["contracts"]["names"] == []
        assert state["contracts"]["code_files"] == []
        assert state["contracts"]["written"] is False
        assert state["contracts"]["validated"] is False

    def test_all_schema_keys_include_new_fields(self):
        state = build_initial_state("implement", "sess-1", "")
        expected_keys = {
            "session_id", "workflow_active", "workflow_type", "phases",
            "tdd", "story_id", "skip", "instructions",
            "agents", "plan", "tasks", "tests", "code_files_to_write",
            "code_files", "quality_check_result", "pr", "ci-check",
            "report_written", "dependencies", "contracts",
        }
        assert set(state.keys()) == expected_keys


# ═══════════════════════════════════════════════════════════════════
# archive_contracts
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(archive_contracts is None, reason="Not yet implemented")
class TestArchiveContracts:
    def test_archives_existing_contracts(self, tmp_path: Path, monkeypatch):
        contracts_dir = tmp_path / ".claude" / "contracts"
        contracts_dir.mkdir(parents=True)
        contracts_path = contracts_dir / "latest-contracts.md"
        contracts_path.write_text("# Contracts\n\n- UserService\n- AuthProvider\n")

        archive_dir = contracts_dir / "archive"

        config = Config()
        monkeypatch.setattr(
            type(config), "contracts_file_path",
            property(lambda self: str(contracts_path)),
        )
        monkeypatch.setattr(
            type(config), "contracts_archive_dir",
            property(lambda self: str(archive_dir)),
        )

        archive_contracts(config)

        assert not contracts_path.exists()
        archived = list(archive_dir.glob("contracts_*.md"))
        assert len(archived) == 1
        assert "UserService" in archived[0].read_text()

    def test_no_contracts_file_does_nothing(self, tmp_path: Path, monkeypatch):
        config = Config()
        monkeypatch.setattr(
            type(config), "contracts_file_path",
            property(lambda self: str(tmp_path / "nonexistent.md")),
        )
        archive_contracts(config)  # should not raise


# ═══════════════════════════════════════════════════════════════════
# Duplicate story guard
# ═══════════════════════════════════════════════════════════════════


from utils.state_store import StateStore


def _seed_active_session(state_path: Path, session_id: str, story_id: str, **extra) -> None:
    """Write an active session entry to the JSONL file."""
    entry = {
        "session_id": session_id,
        "workflow_active": True,
        "workflow_type": "implement",
        "story_id": story_id,
        "phases": [{"name": "explore", "status": "completed"}],
        **extra,
    }
    with open(state_path, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


class TestDuplicateStoryGuard:
    """Default: initialize fails if another active session has the same story_id."""

    def test_blocks_duplicate_story(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-sess", "SK-001")

        with pytest.raises(ValueError, match="SK-001.*already active"):
            initialize("implement", "new-sess", "SK-001 build a form", state_path)

    def test_allows_different_story(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-sess", "SK-001")

        # SK-002 is different — should succeed
        initialize("implement", "new-sess", "SK-002 build a form", state_path)
        store = StateStore(state_path, session_id="new-sess")
        assert store.get("story_id") == "SK-002"

    def test_allows_when_no_active_sessions(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        state_path.write_text("")

        initialize("implement", "new-sess", "SK-001 build a form", state_path)
        store = StateStore(state_path, session_id="new-sess")
        assert store.get("story_id") == "SK-001"

    def test_allows_when_old_session_inactive(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        entry = json.dumps({
            "session_id": "old-sess",
            "workflow_active": False,
            "story_id": "SK-001",
        }, separators=(",", ":"))
        state_path.write_text(entry + "\n")

        initialize("implement", "new-sess", "SK-001 build a form", state_path)
        store = StateStore(state_path, session_id="new-sess")
        assert store.get("story_id") == "SK-001"

    def test_build_without_story_id_skips_guard(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        state_path.write_text("")

        initialize("build", "new-sess", "build a login form", state_path)
        store = StateStore(state_path, session_id="new-sess")
        assert store.get("workflow_active") is True


class TestResetFlag:
    """--reset deactivates all old sessions for the story and starts fresh."""

    def test_reset_deactivates_old_sessions(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-1", "SK-001")
        _seed_active_session(state_path, "old-2", "SK-001")

        initialize("implement", "new-sess", "--reset SK-001 build", state_path)

        # Old sessions deactivated
        old1 = StateStore(state_path, session_id="old-1")
        old2 = StateStore(state_path, session_id="old-2")
        assert old1.get("workflow_active") is False
        assert old2.get("workflow_active") is False

        # New session is fresh (no phases from old)
        new = StateStore(state_path, session_id="new-sess")
        assert new.get("workflow_active") is True
        assert new.get("phases") == []

    def test_reset_strips_flag_from_instructions(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old", "SK-001")

        initialize("implement", "new-sess", "--reset SK-001 build a form", state_path)
        new = StateStore(state_path, session_id="new-sess")
        assert new.get("instructions") == "build a form"


class TestTakeoverFlag:
    """--takeover copies latest session state and deactivates all old sessions."""

    def test_takeover_copies_state(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(
            state_path, "old-sess", "SK-001",
            plan={"file_path": "plan.md", "written": True, "revised": False, "reviews": []},
            tasks=["Build login"],
        )

        initialize("implement", "new-sess", "--takeover SK-001 build", state_path)

        new = StateStore(state_path, session_id="new-sess")
        assert new.get("workflow_active") is True
        assert new.get("plan", {}).get("written") is True
        assert new.get("tasks") == ["Build login"]

    def test_takeover_deactivates_all_old(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-1", "SK-001")
        _seed_active_session(state_path, "old-2", "SK-001")

        initialize("implement", "new-sess", "--takeover SK-001 build", state_path)

        old1 = StateStore(state_path, session_id="old-1")
        old2 = StateStore(state_path, session_id="old-2")
        assert old1.get("workflow_active") is False
        assert old2.get("workflow_active") is False

    def test_takeover_copies_latest_session(self, tmp_path: Path):
        """When multiple active sessions exist, takeover copies the last one."""
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-1", "SK-001", tasks=["Task A"])
        _seed_active_session(state_path, "old-2", "SK-001", tasks=["Task B"])

        initialize("implement", "new-sess", "--takeover SK-001 build", state_path)

        new = StateStore(state_path, session_id="new-sess")
        # Should copy from old-2 (last in file)
        assert new.get("tasks") == ["Task B"]

    def test_takeover_updates_session_id(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old-sess", "SK-001")

        initialize("implement", "new-sess", "--takeover SK-001 build", state_path)

        new = StateStore(state_path, session_id="new-sess")
        assert new.get("session_id") == "new-sess"

    def test_takeover_preserves_old_instructions(self, tmp_path: Path):
        """Takeover copies state — instructions come from the old session, not args."""
        state_path = tmp_path / "state.jsonl"
        _seed_active_session(state_path, "old", "SK-001", instructions="original task")

        initialize("implement", "new-sess", "--takeover SK-001 new task", state_path)
        new = StateStore(state_path, session_id="new-sess")
        assert new.get("instructions") == "original task"


class TestParseInstructionsFlags:
    """--reset and --takeover should be stripped from instructions."""

    def test_strips_reset(self):
        assert parse_instructions("--reset SK-001 build a form") == "build a form"

    def test_strips_takeover(self):
        assert parse_instructions("--takeover SK-001 build a form") == "build a form"

    def test_strips_all_flags(self):
        result = parse_instructions("--tdd --reset --skip-explore SK-001 build")
        assert result == "build"

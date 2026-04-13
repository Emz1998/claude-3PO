import re
import tomllib
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, config_path: Path | None = None):
        self._path = config_path or Path(__file__).parent / "config.toml"
        with open(self._path, "rb") as f:
            self._data: dict[str, Any] = tomllib.load(f)

    # ── Raw accessors ──────────────────────────────────────────────

    @property
    def read_only_phases(self) -> list[str]:
        return self._data.get("READ_ONLY_PHASES", [])

    @property
    def code_write_phases(self) -> list[str]:
        return self._data.get("CODE_WRITE_PHASES", [])

    @property
    def code_edit_phases(self) -> list[str]:
        return self._data.get("CODE_EDIT_PHASES", [])

    @property
    def docs_write_phases(self) -> list[str]:
        return self._data.get("DOCS_WRITE_PHASES", [])

    @property
    def docs_edit_phases(self) -> list[str]:
        return self._data.get("DOCS_EDIT_PHASES", [])

    @property
    def checkpoint_phase(self) -> list[str]:
        return self._data.get("CHECKPOINT_PHASE", [])

    @property
    def safe_domains(self) -> list[str]:
        return self._data.get("SAFE_DOMAINS", [])

    @property
    def required_agents(self) -> dict[str, str]:
        return self._data.get("REQUIRED_AGENTS", {})

    @property
    def score_thresholds(self) -> dict[str, dict[str, int]]:
        return self._data.get("SCORE_THRESHOLDS", {})

    # ── Agent limits ───────────────────────────────────────────────

    def get_agent_max(self, key: str) -> int:
        return self._data.get(key, 0)

    @property
    def explore_max(self) -> int:
        return self._data.get("EXPLORE_MAX", 3)

    @property
    def research_max(self) -> int:
        return self._data.get("RESEARCH_MAX", 2)

    @property
    def plan_max(self) -> int:
        return self._data.get("PLAN_MAX", 1)

    @property
    def plan_review_max(self) -> int:
        return self._data.get("PLAN_REVIEW_MAX", 3)

    @property
    def test_reviewer_max(self) -> int:
        return self._data.get("TEST_REVIEWER_MAX", 3)

    @property
    def qa_specialist_max(self) -> int:
        return self._data.get("QA_SPECIALIST_MAX", 1)

    @property
    def code_reviewer_max(self) -> int:
        return self._data.get("CODE_REVIEWER_MAX", 3)

    # ── Required agents ────────────────────────────────────────────

    def get_required_agent(self, phase: str) -> str:
        return self.required_agents.get(phase, "")

    def is_agent_required(self, phase: str, agent_name: str) -> bool:
        return self.get_required_agent(phase) == agent_name

    def get_agent_max_count(self, agent_name: str) -> int:
        """Look up MAX invocation limit for an agent by name.

        Converts PascalCase to UPPER_SNAKE: PlanReview -> PLAN_REVIEW_MAX,
        QASpecialist -> QA_SPECIALIST_MAX.
        """
        snake = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", agent_name
        )
        key = f"{snake.upper()}_MAX"
        return self._data.get(key, 1)

    # ── Phases ─────────────────────────────────────────────────────

    @property
    def main_phases(self) -> list[str]:
        return self._data.get("MAIN_PHASES", [])

    def is_main_phase(self, phase: str) -> bool:
        return phase in self.main_phases

    # ── Score thresholds ───────────────────────────────────────────

    def get_score_threshold(self, phase: str, score_type: str) -> int:
        return self.score_thresholds.get(phase, {}).get(score_type, 0)

    # ── File paths ─────────────────────────────────────────────────

    @property
    def file_paths(self) -> dict[str, str]:
        return self._data.get("FILE_PATHS", {})

    @property
    def plan_file_path(self) -> str:
        return self.file_paths.get("PLAN_FILE_PATH", "")

    @property
    def plan_archive_dir(self) -> str:
        return self.file_paths.get("PLAN_ARCHIVE_DIR", "")

    @property
    def test_file_path(self) -> str:
        return self.file_paths.get("TEST_FILE_PATH", "")

    @property
    def code_file_path(self) -> str:
        return self.file_paths.get("CODE_FILE_PATH", "")

    @property
    def report_file_path(self) -> str:
        return self.file_paths.get("REPORT_FILE_PATH", "")

    @property
    def contracts_file_path(self) -> str:
        return self.file_paths.get("CONTRACTS_FILE_PATH", "")

    @property
    def contracts_archive_dir(self) -> str:
        return self.file_paths.get("CONTRACTS_ARCHIVE_DIR", "")

    @property
    def log_file(self) -> str:
        return self.file_paths.get("LOG_FILE", "")

    @property
    def debug_log_file(self) -> str:
        return self.file_paths.get("DEBUG_LOG_FILE", "")

    @property
    def default_state_jsonl(self) -> str:
        return self.file_paths.get("DEFAULT_STATE_JSONL", "")

    # ── Phase classification helpers ───────────────────────────────

    def is_read_only_phase(self, phase: str) -> bool:
        return phase in self.read_only_phases

    def is_code_write_phase(self, phase: str) -> bool:
        return phase in self.code_write_phases

    def is_code_edit_phase(self, phase: str) -> bool:
        return phase in self.code_edit_phases

    def is_docs_write_phase(self, phase: str) -> bool:
        return phase in self.docs_write_phases

    def is_docs_edit_phase(self, phase: str) -> bool:
        return phase in self.docs_edit_phases

    def is_checkpoint_phase(self, phase: str) -> bool:
        return phase in self.checkpoint_phase

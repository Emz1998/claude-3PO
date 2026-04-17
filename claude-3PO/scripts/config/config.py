import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, config_path: Path | None = None):
        self._path = config_path or Path(__file__).parent / "config.json"
        with open(self._path, "r") as f:
            self._data: dict[str, Any] = json.load(f)
        self._phase_list: list[dict] = self._data.get("phases", [])
        self._phase_map: dict[str, dict] = {p["name"]: p for p in self._phase_list}

    # ── Phase queries (derived from phases array) ─────────────────

    def _phases_with(self, flag: str) -> list[str]:
        return [p["name"] for p in self._phase_list if p.get(flag)]

    def get_phases(self, workflow_type: str) -> list[str]:
        return [p["name"] for p in self._phase_list if workflow_type in p.get("workflows", [])]

    @property
    def build_phases(self) -> list[str]:
        return self.get_phases("build")

    @property
    def implement_phases(self) -> list[str]:
        return self.get_phases("implement")

    @property
    def main_phases(self) -> list[str]:
        return self.build_phases

    @property
    def auto_phases(self) -> list[str]:
        return self._phases_with("auto")

    @property
    def read_only_phases(self) -> list[str]:
        return self._phases_with("read_only")

    @property
    def code_write_phases(self) -> list[str]:
        return self._phases_with("code_write")

    @property
    def code_edit_phases(self) -> list[str]:
        return self._phases_with("code_edit")

    @property
    def docs_write_phases(self) -> list[str]:
        return self._phases_with("docs_write")

    @property
    def docs_edit_phases(self) -> list[str]:
        return self._phases_with("docs_edit")

    @property
    def checkpoint_phase(self) -> list[str]:
        return self._phases_with("checkpoint")

    def is_auto_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("auto", False)

    def is_main_phase(self, phase: str) -> bool:
        return phase in self.main_phases

    def is_read_only_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("read_only", False)

    def is_code_write_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("code_write", False)

    def is_code_edit_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("code_edit", False)

    def is_docs_write_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("docs_write", False)

    def is_docs_edit_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("docs_edit", False)

    def is_checkpoint_phase(self, phase: str) -> bool:
        return self._phase_map.get(phase, {}).get("checkpoint", False)

    # ── Agents (derived from phases + agents map) ─────────────────

    def get_required_agent(self, phase: str) -> str:
        return self._phase_map.get(phase, {}).get("agent", "")

    def is_agent_required(self, phase: str, agent_name: str) -> bool:
        return self.get_required_agent(phase) == agent_name

    def get_agent_max_count(self, agent_name: str) -> int:
        counts = [
            p["agent_count"]
            for p in self._phase_list
            if p.get("agent") == agent_name and "agent_count" in p
        ]
        return max(counts) if counts else 1

    @property
    def required_agents(self) -> dict[str, str]:
        return {p["name"]: p["agent"] for p in self._phase_list if p.get("agent")}

    # ── Plan templates ────────────────────────────────────────────

    def _plan_template(self, workflow_type: str) -> dict[str, Any]:
        return self._data.get("plan_templates", {}).get(workflow_type, {})

    def get_plan_required_sections(self, workflow_type: str) -> list[str]:
        return self._plan_template(workflow_type).get("required_sections", [])

    def get_plan_bullet_sections(self, workflow_type: str) -> list[str]:
        return self._plan_template(workflow_type).get("bullet_sections", [])

    @property
    def build_plan_required_sections(self) -> list[str]:
        return self.get_plan_required_sections("build")

    @property
    def build_plan_bullet_sections(self) -> list[str]:
        return self.get_plan_bullet_sections("build")

    @property
    def implement_plan_required_sections(self) -> list[str]:
        return self.get_plan_required_sections("implement")

    # ── Score thresholds ──────────────────────────────────────────

    @property
    def score_thresholds(self) -> dict[str, dict[str, int]]:
        return self._data.get("score_thresholds", {})

    def get_score_threshold(self, phase: str, score_type: str) -> int:
        return self.score_thresholds.get(phase, {}).get(score_type, 0)

    # ── Safe domains ──────────────────────────────────────────────

    @property
    def safe_domains(self) -> list[str]:
        return self._data.get("safe_domains", [])

    # ── Paths ─────────────────────────────────────────────────────

    def _paths(self) -> dict[str, str]:
        return self._data.get("paths", {})

    @property
    def plan_file_path(self) -> str:
        return self._paths().get("plan_file", "")

    @property
    def plan_archive_dir(self) -> str:
        return self._paths().get("plan_archive_dir", "")

    @property
    def test_file_path(self) -> str:
        return self._paths().get("test_file", "")

    @property
    def code_file_path(self) -> str:
        return self._paths().get("code_file", "")

    @property
    def report_file_path(self) -> str:
        return self._paths().get("report_file", "")

    @property
    def contracts_file_path(self) -> str:
        return self._paths().get("contracts_file", "")

    @property
    def contracts_archive_dir(self) -> str:
        return self._paths().get("contracts_archive_dir", "")

    @property
    def log_file(self) -> str:
        return self._paths().get("log_file", "")

    @property
    def debug_log_file(self) -> str:
        return self._paths().get("debug_log_file", "")

    @property
    def default_state_jsonl(self) -> str:
        return self._paths().get("state_jsonl", "")

    # ── Specs review cap ──────────────────────────────────────────

    @property
    def specs_max_report_retries(self) -> int:
        return int(
            self._data.get("specs_phases", {}).get("max_report_retries", 3)
        )

    # ── Specs schemas ─────────────────────────────────────────────

    def specs_schema(self, doc_type: str) -> dict[str, Any]:
        return self._data.get("specs_schemas", {}).get(doc_type, {})

    def specs_metadata_fields(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("metadata_fields", [])

    def specs_valid_statuses(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("valid_statuses", [])

    def specs_required_sections(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("required_sections", [])

    def specs_required_subsections(self, doc_type: str) -> dict[str, list[str]]:
        return self.specs_schema(doc_type).get("required_subsections", {})

    def specs_allowed_extra_sections(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("allowed_extra_sections", [])

    def specs_required_tables(self, doc_type: str) -> list[dict[str, str]]:
        return self.specs_schema(doc_type).get("required_tables", [])

    def specs_valid_priorities(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("valid_priorities", [])

    def specs_valid_item_types(self, doc_type: str) -> list[str]:
        return self.specs_schema(doc_type).get("valid_item_types", [])

    def specs_story_type_names(self, doc_type: str) -> dict[str, str]:
        return self.specs_schema(doc_type).get("story_type_names", {})

    # ── Specs paths ───────────────────────────────────────────────

    @property
    def product_vision_file_path(self) -> str:
        return self._paths().get("product_vision_file", "")

    @property
    def decisions_file_path(self) -> str:
        return self._paths().get("decisions_file", "")

    @property
    def architecture_file_path(self) -> str:
        return self._paths().get("architecture_file", "")

    @property
    def backlog_md_file_path(self) -> str:
        return self._paths().get("backlog_md_file", "")

    @property
    def backlog_json_file_path(self) -> str:
        return self._paths().get("backlog_json_file", "")

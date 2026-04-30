import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, config_path: Path | None = None):

        self._path = config_path or Path(__file__).parent / "config.json"
        with open(self._path, "r") as f:
            self._data: dict[str, Any] = json.load(f)
        self._phase_list: list[dict] = self._data.get("phases", [])
        self._phase_map: dict[str, dict] = {s["name"]: s for s in self._phase_list}

    # ── Phase queries (derived from phases array) ─────────────────

    def _phases_with(self, flag: str) -> list[str]:

        return [s["name"] for s in self._phase_list if s.get(flag)]

    def get_phases(self, key: str, value: Any) -> list[dict[str, Any]]:
        return [s for s in self._phase_list if s.get(key) == value]

    def get_phases_by_workflow(self, workflow_type: str) -> list[dict[str, Any]]:
        return [p for p in self._phase_list if workflow_type in p.get("workflows", [])]

    def get_phase_names_by_workflow(self, workflow_type: str) -> list[str]:
        return [p["name"] for p in self.get_phases_by_workflow(workflow_type)]

    def get_modes(self, phase_name: str) -> list[dict[str, Any]]:
        return self._phase_map.get(phase_name, {}).get("modes", [])

    def _get_read_only_phases(self) -> list[dict[str, Any]]:
        return [p for p in self._phase_list if p.get("modes") is None]

    def _get_no_restrictions_phases(self) -> list[dict[str, Any]]:
        return [p for p in self._phase_list if p.get("modes") == "*"]

    def _get_edit_only_phases(self) -> list[dict[str, Any]]:
        phases = []
        for phase in self._phase_list:
            modes = phase.get("modes", None)
            is_dict = isinstance(modes, dict)
            if is_dict and "edit-only" in modes.keys():
                phases.append(phase)
        return phases

    def _get_commands_only_phases(self) -> list[dict[str, Any]]:
        return [p for p in self._phase_list if p.get("modes") == "commands-only"]

    @staticmethod
    def _convert_to_name_list(phases: list[dict[str, Any]]) -> list[str]:
        return [phase["name"] for phase in phases]

    def get_phases_by_mode(self, mode_type: str, names_only: bool = False) -> list:
        phases = []

        if mode_type == "read-only":
            phases = self._get_read_only_phases()

        elif mode_type == "no-restrictions":
            phases = self._get_no_restrictions_phases()
        else:
            for phase in self._phase_list:
                modes = phase.get("modes", None)
                is_dict = isinstance(modes, dict)
                if is_dict and mode_type in modes.keys():
                    phases.append(phase)
        return self._convert_to_name_list(phases) if names_only else phases

    def get_agent(self, phase_name: str, agent_name: str) -> dict[str, Any] | None:
        for phase in self._phase_list:
            if phase["name"] == phase_name:
                agents_list = phase.get("agents", [])
                return next((a for a in agents_list if a["name"] == agent_name), {})
        return {}

    def get_agents_by_phase(self, phase_name: str) -> list[dict[str, Any]]:
        return [a for a in self._phase_map.get(phase_name, {}).get("agents", [])]

    def get_agent_names_by_phase(self, phase_name: str) -> list[str]:
        return [a["name"] for a in self.get_agents_by_phase(phase_name)]

    def get_review_agents(self) -> list[str]:
        review_agents = self.get_agents_by_phase("review")
        return [a["name"] for a in review_agents]

    # ── Score thresholds ──────────────────────────────────────────

    def get_score_threshold(self, phase: str, score_type: str) -> int:
        return self._data.get("score_thresholds", {}).get(phase, {}).get(score_type, 0)

    # ── Safe domains ──────────────────────────────────────────────

    @property
    def safe_domains(self) -> list[str]:

        return self._data.get("safe_domains", [])

    # ── Paths ─────────────────────────────────────────────────────

    def get_file_path(self, query: str) -> str:
        return self._data.get("file_paths", {}).get(query, "")

    # ── Coding allowed ────────────────────────────────────────────

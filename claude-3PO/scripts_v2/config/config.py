import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, config_path: Path | None = None):

        self._path = config_path or Path(__file__).parent / "config.json"
        with open(self._path, "r") as f:
            self._data: dict[str, Any] = json.load(f)
        self._skill_list: list[dict] = self._data.get("skills", [])
        self._skill_map: dict[str, dict] = {s["name"]: s for s in self._skill_list}

    # ── Skill queries (derived from skills array) ─────────────────

    def _skills_with(self, flag: str) -> list[str]:

        return [s["name"] for s in self._skill_list if s.get(flag)]

    def get_skills(self, key: str, value: Any) -> list[dict[str, Any]]:
        return [s for s in self._skill_list if s.get(key) == value]

    def get_skills_by_workflow(self, workflow_type: str) -> list[dict[str, Any]]:
        return [p for p in self._skill_list if workflow_type in p.get("workflows", [])]

    def get_skill_names_by_workflow(self, workflow_type: str) -> list[str]:
        return [p["name"] for p in self.get_skills_by_workflow(workflow_type)]

    def get_modes(self, skill_name: str) -> list[dict[str, Any]]:
        return self._skill_map.get(skill_name, {}).get("modes", [])

    def get_skills_by_mode(
        self, mode_type: str, extensions: list[str] | None = None
    ) -> list[str]:
        skills = []
        for skill in self._skill_list:
            for mode in skill.get("modes", []):
                m_type = mode.get("type")
                m_extensions = mode.get("extensions")
                if m_type != mode_type:
                    continue
                if extensions is not None and set(m_extensions or []) != set(
                    extensions
                ):
                    continue
                skills.append(skill["name"])
                break  # avoid duplicates if a skill has multiple matching modes
        return skills

    def get_extensions(self, skill_name: str, mode_type: str) -> list[str]:
        modes = self.get_modes(skill_name)
        return [m["extensions"] for m in modes if m.get("type") == mode_type]

    def get_agent(self, skill_name: str, agent_name: str) -> dict[str, Any] | None:
        for skill in self._skill_list:
            if skill["name"] == skill_name:
                agents_list = skill.get("agents", [])
                return next((a for a in agents_list if a["name"] == agent_name), {})
        return {}

    def get_agents_by_skill(self, skill_name: str) -> list[dict[str, Any]]:
        return [a for a in self._skill_map.get(skill_name, {}).get("agents", [])]

    def get_agent_names_by_skill(self, skill_name: str) -> list[str]:
        return [a["name"] for a in self.get_agents_by_skill(skill_name)]

    # ── Score thresholds ──────────────────────────────────────────

    def get_score_threshold(self, skill: str, score_type: str) -> int:
        return self._data.get("score_thresholds", {}).get(skill, {}).get(score_type, 0)

    # ── Safe domains ──────────────────────────────────────────────

    @property
    def safe_domains(self) -> list[str]:

        return self._data.get("safe_domains", [])

    # ── Paths ─────────────────────────────────────────────────────

    def get_path(self, query: str) -> str:
        return self._data.get("paths", {}).get(query, "")

    # ── Coding allowed ────────────────────────────────────────────

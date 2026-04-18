import json
from pathlib import Path
from typing import Any


class Config:
    """Single source of truth for workflow configuration.

    Loaded once at process start from ``config/config.json`` and cached by
    :func:`config.get_config`. Most properties on this class derive from the
    ``phases`` array in that JSON file: each phase is a dict with a name plus
    boolean flags (``auto``, ``read_only``, ``code_write``, ``code_edit``,
    ``docs_write``, ``docs_edit``, ``checkpoint``) and an optional ``agent``
    name. The ``*_phases`` properties below are one-line aggregations of those
    flags via :meth:`_phases_with`, so adding a new phase or flipping a flag
    in JSON immediately updates every consumer — guards, hooks, and validators
    never hard-code phase names.

    Plan templates, score thresholds, safe domains, file paths, and specs
    settings are read from sibling top-level keys with the same JSON-as-truth
    pattern.

    Example:
        >>> cfg = Config()  # doctest: +SKIP — reads scripts/config/config.json
    """

    def __init__(self, config_path: Path | None = None):
        """
        Load and parse ``config.json`` into in-memory lookup structures.

        Args:
            config_path (Path | None): Optional override for the config file
                location; defaults to ``config/config.json`` next to this module.

        Example:
            >>> Config()  # doctest: +SKIP — reads scripts/config/config.json
        """
        self._path = config_path or Path(__file__).parent / "config.json"
        with open(self._path, "r") as f:
            self._data: dict[str, Any] = json.load(f)
        self._phase_list: list[dict] = self._data.get("phases", [])
        self._phase_map: dict[str, dict] = {p["name"]: p for p in self._phase_list}

    # ── Phase queries (derived from phases array) ─────────────────

    def _phases_with(self, flag: str) -> list[str]:
        """
        Return phase names whose JSON entry has a truthy ``flag`` field.

        This is the single engine behind every ``*_phases`` property below —
        each property just hands a flag name to this helper. Keeps the schema
        purely data-driven: a new boolean flag on a phase becomes queryable by
        adding a one-line property that calls this method.

        Args:
            flag (str): Boolean flag name to check on each phase entry
                (e.g. ``"auto"``, ``"code_write"``).

        Returns:
            list[str]: Names of phases where ``phase.get(flag)`` is truthy,
            in the order they appear in ``config.json``.

        Example:
            >>> cfg = Config()
            >>> "plan" in cfg._phases_with("auto")  # doctest: +SKIP
            True
        """
        return [p["name"] for p in self._phase_list if p.get(flag)]

    def get_phases(self, workflow_type: str) -> list[str]:
        """
        Return phases that participate in a given workflow type.

        Args:
            workflow_type (str): Workflow identifier (e.g. ``"build"``,
                ``"implement"``) matched against each phase's ``workflows`` list.

        Returns:
            list[str]: Phase names whose ``workflows`` array contains
            ``workflow_type``, in JSON declaration order.

        Example:
            >>> get_config().get_phases("build")  # doctest: +SKIP
            ['clarify', 'explore', 'research', 'decision', 'plan', 'plan-review', 'create-tasks', 'write-tests', 'test-review', 'write-code', 'quality-check', 'code-review', 'pr-create', 'ci-check', 'write-report']
        """
        return [p["name"] for p in self._phase_list if workflow_type in p.get("workflows", [])]

    @property
    def build_phases(self) -> list[str]:
        """Phases participating in the ``build`` workflow.

        Example:
            >>> get_config().build_phases  # doctest: +SKIP
            ['clarify', 'explore', 'research', 'decision', 'plan', 'plan-review', 'create-tasks', 'write-tests', 'test-review', 'write-code', 'quality-check', 'code-review', 'pr-create', 'ci-check', 'write-report']
        """
        return self.get_phases("build")

    @property
    def implement_phases(self) -> list[str]:
        """Phases participating in the ``implement`` workflow.

        Example:
            >>> get_config().implement_phases  # doctest: +SKIP
            ['plan', 'write-code', 'write-report']
        """
        return self.get_phases("implement")

    @property
    def main_phases(self) -> list[str]:
        """Alias of :attr:`build_phases` (the canonical "main" pipeline).

        Example:
            >>> get_config().main_phases == get_config().build_phases  # doctest: +SKIP
            True
        """
        return self.build_phases

    @property
    def auto_phases(self) -> list[str]:
        """Phases that the orchestrator may advance without user prompt.

        Example:
            >>> "write-code" in get_config().auto_phases  # doctest: +SKIP
            True
        """
        return self._phases_with("auto")

    @property
    def read_only_phases(self) -> list[str]:
        """Phases where write tools are blocked by guards.

        Example:
            >>> get_config().read_only_phases  # doctest: +SKIP
            ['plan-review', 'code-review']
        """
        return self._phases_with("read_only")

    @property
    def code_write_phases(self) -> list[str]:
        """Phases where creating new code files is allowed.

        Example:
            >>> get_config().code_write_phases  # doctest: +SKIP
            ['write-tests', 'write-code']
        """
        return self._phases_with("code_write")

    @property
    def code_edit_phases(self) -> list[str]:
        """Phases where editing existing code files is allowed.

        Example:
            >>> "write-code" in get_config().code_edit_phases  # doctest: +SKIP
            True
        """
        return self._phases_with("code_edit")

    @property
    def docs_write_phases(self) -> list[str]:
        """Phases where creating new docs/spec files is allowed.

        Example:
            >>> "plan" in get_config().docs_write_phases  # doctest: +SKIP
            True
        """
        return self._phases_with("docs_write")

    @property
    def docs_edit_phases(self) -> list[str]:
        """Phases where editing existing docs/spec files is allowed.

        Example:
            >>> get_config().docs_edit_phases  # doctest: +SKIP
            ['plan', 'write-report']
        """
        return self._phases_with("docs_edit")

    @property
    def checkpoint_phase(self) -> list[str]:
        """Phases flagged as checkpoints (workflow may pause/resume here).

        Example:
            >>> get_config().checkpoint_phase  # doctest: +SKIP
            ['plan-review']
        """
        return self._phases_with("checkpoint")

    def is_auto_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``auto``.

        Example:
            >>> get_config().is_auto_phase("write-code")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("auto", False)

    def is_main_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is in the main (build) pipeline.

        Example:
            >>> get_config().is_main_phase("plan")  # doctest: +SKIP
            True
        """
        return phase in self.main_phases

    def is_read_only_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``read_only``.

        Example:
            >>> get_config().is_read_only_phase("plan-review")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("read_only", False)

    def is_code_write_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``code_write``.

        Example:
            >>> get_config().is_code_write_phase("write-code")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("code_write", False)

    def is_code_edit_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``code_edit``.

        Example:
            >>> get_config().is_code_edit_phase("write-code")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("code_edit", False)

    def is_docs_write_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``docs_write``.

        Example:
            >>> get_config().is_docs_write_phase("plan")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("docs_write", False)

    def is_docs_edit_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``docs_edit``.

        Example:
            >>> get_config().is_docs_edit_phase("write-report")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("docs_edit", False)

    def is_checkpoint_phase(self, phase: str) -> bool:
        """Return whether ``phase`` is flagged ``checkpoint``.

        Example:
            >>> get_config().is_checkpoint_phase("plan-review")  # doctest: +SKIP
            True
        """
        return self._phase_map.get(phase, {}).get("checkpoint", False)

    # ── Agents (derived from phases + agents map) ─────────────────

    def get_required_agent(self, phase: str) -> str:
        """Return the subagent name required for ``phase`` (empty if none).

        Example:
            >>> get_config().get_required_agent("plan")  # doctest: +SKIP
            'planner'
        """
        return self._phase_map.get(phase, {}).get("agent", "")

    def is_agent_required(self, phase: str, agent_name: str) -> bool:
        """Return whether ``agent_name`` is the required agent for ``phase``.

        Example:
            >>> get_config().is_agent_required("plan", "planner")  # doctest: +SKIP
            True
        """
        return self.get_required_agent(phase) == agent_name

    def get_agent_max_count(self, agent_name: str) -> int:
        """Return the max parallel ``agent_count`` declared for ``agent_name``.

        Example:
            >>> get_config().get_agent_max_count("coder")  # doctest: +SKIP
            3
        """
        counts = [
            p["agent_count"]
            for p in self._phase_list
            if p.get("agent") == agent_name and "agent_count" in p
        ]
        return max(counts) if counts else 1

    @property
    def required_agents(self) -> dict[str, str]:
        """Mapping of phase name to its required subagent name.

        Example:
            >>> get_config().required_agents.get("plan")  # doctest: +SKIP
            'planner'
        """
        return {p["name"]: p["agent"] for p in self._phase_list if p.get("agent")}

    # ── Plan templates ────────────────────────────────────────────

    def _plan_template(self, workflow_type: str) -> dict[str, Any]:
        """Return the raw ``plan_templates[workflow_type]`` block (or ``{}``).

        Example:
            >>> get_config()._plan_template("build")  # doctest: +SKIP
            {'required_sections': [...], 'bullet_sections': [...]}
        """
        return self._data.get("plan_templates", {}).get(workflow_type, {})

    def get_plan_required_sections(self, workflow_type: str) -> list[str]:
        """Required H2 sections in the plan markdown for ``workflow_type``.

        Example:
            >>> get_config().get_plan_required_sections("build")  # doctest: +SKIP
            ['Goal', 'Tasks', 'Acceptance Criteria']
        """
        return self._plan_template(workflow_type).get("required_sections", [])

    def get_plan_bullet_sections(self, workflow_type: str) -> list[str]:
        """Plan sections that must be expressed as bullet lists.

        Example:
            >>> get_config().get_plan_bullet_sections("build")  # doctest: +SKIP
            ['Tasks', 'Acceptance Criteria']
        """
        return self._plan_template(workflow_type).get("bullet_sections", [])

    @property
    def build_plan_required_sections(self) -> list[str]:
        """Required plan sections for the ``build`` workflow.

        Example:
            >>> get_config().build_plan_required_sections  # doctest: +SKIP
            ['Goal', 'Tasks', 'Acceptance Criteria']
        """
        return self.get_plan_required_sections("build")

    @property
    def build_plan_bullet_sections(self) -> list[str]:
        """Bullet-only plan sections for the ``build`` workflow.

        Example:
            >>> get_config().build_plan_bullet_sections  # doctest: +SKIP
            ['Tasks', 'Acceptance Criteria']
        """
        return self.get_plan_bullet_sections("build")

    @property
    def implement_plan_required_sections(self) -> list[str]:
        """Required plan sections for the ``implement`` workflow.

        Example:
            >>> get_config().implement_plan_required_sections  # doctest: +SKIP
            ['Goal', 'Tasks']
        """
        return self.get_plan_required_sections("implement")

    # ── Score thresholds ──────────────────────────────────────────

    @property
    def score_thresholds(self) -> dict[str, dict[str, int]]:
        """Per-phase score thresholds (``{phase: {score_type: threshold}}``).

        Example:
            >>> get_config().score_thresholds.get("plan-review")  # doctest: +SKIP
            {'clarity': 8, 'completeness': 8}
        """
        return self._data.get("score_thresholds", {})

    def get_score_threshold(self, phase: str, score_type: str) -> int:
        """Return the minimum passing score for ``score_type`` in ``phase``.

        Example:
            >>> get_config().get_score_threshold("plan-review", "clarity")  # doctest: +SKIP
            8
        """
        return self.score_thresholds.get(phase, {}).get(score_type, 0)

    # ── Safe domains ──────────────────────────────────────────────

    @property
    def safe_domains(self) -> list[str]:
        """Domains agents may fetch from without extra confirmation.

        Example:
            >>> "github.com" in get_config().safe_domains  # doctest: +SKIP
            True
        """
        return self._data.get("safe_domains", [])

    # ── Paths ─────────────────────────────────────────────────────

    def _paths(self) -> dict[str, str]:
        """Return the raw ``paths`` block from config.json (or ``{}``).

        Example:
            >>> "plan_file" in get_config()._paths()  # doctest: +SKIP
            True
        """
        return self._data.get("paths", {})

    @property
    def plan_file_path(self) -> str:
        """Path to the active plan markdown file.

        Example:
            >>> get_config().plan_file_path  # doctest: +SKIP
            '.claude/plans/active.md'
        """
        return self._paths().get("plan_file", "")

    @property
    def plan_archive_dir(self) -> str:
        """Directory where completed plans are archived.

        Example:
            >>> get_config().plan_archive_dir  # doctest: +SKIP
            '.claude/plans/archive'
        """
        return self._paths().get("plan_archive_dir", "")

    @property
    def test_file_path(self) -> str:
        """Path template for generated test files.

        Example:
            >>> get_config().test_file_path  # doctest: +SKIP
            'tests/test_{name}.py'
        """
        return self._paths().get("test_file", "")

    @property
    def code_file_path(self) -> str:
        """Path template for generated code files.

        Example:
            >>> get_config().code_file_path  # doctest: +SKIP
            'src/{name}.py'
        """
        return self._paths().get("code_file", "")

    @property
    def report_file_path(self) -> str:
        """Path to the workflow's final report file.

        Example:
            >>> get_config().report_file_path  # doctest: +SKIP
            '.claude/reports/active.md'
        """
        return self._paths().get("report_file", "")

    @property
    def clarity_review_prompt_file_path(self) -> str:
        """Path to the headless-Claude clarity-review prompt template.

        Example:
            >>> get_config().clarity_review_prompt_file_path  # doctest: +SKIP
            'templates/clarity-review.md'
        """
        return self._paths().get("clarity_review_prompt_file", "")

    @property
    def log_file(self) -> str:
        """Path to the standard workflow log file.

        Example:
            >>> get_config().log_file  # doctest: +SKIP
            '.claude/logs/workflow.log'
        """
        return self._paths().get("log_file", "")

    @property
    def debug_log_file(self) -> str:
        """Path to the verbose debug log file.

        Example:
            >>> get_config().debug_log_file  # doctest: +SKIP
            '.claude/logs/debug.log'
        """
        return self._paths().get("debug_log_file", "")

    @property
    def default_state_jsonl(self) -> str:
        """Default path to the persisted ``state.jsonl`` snapshot stream.

        Example:
            >>> get_config().default_state_jsonl  # doctest: +SKIP
            '.claude/state.jsonl'
        """
        return self._paths().get("state_jsonl", "")

    # ── Clarify safety ceiling ────────────────────────────────────

    @property
    def clarify_max_iterations(self) -> int:
        """Max number of AskUserQuestion iterations allowed in clarify.

        Defaults to 10 — beyond that, the guardrail blocks further
        AskUserQuestion calls so an unbounded prompt clarification
        loop can't run forever.

        Example:
            >>> get_config().clarify_max_iterations  # doctest: +SKIP
            10
        """
        return int(self._data.get("clarify", {}).get("max_iterations", 10))

    # ── Specs review cap ──────────────────────────────────────────

    @property
    def specs_max_report_retries(self) -> int:
        """Max times a specs reviewer may re-request an agent report (default 3).

        Example:
            >>> get_config().specs_max_report_retries  # doctest: +SKIP
            3
        """
        return int(
            self._data.get("specs_phases", {}).get("max_report_retries", 3)
        )

    # ── Templates directory ───────────────────────────────────────

    @property
    def templates_dir(self) -> Path:
        """Absolute path to the repo's ``templates/`` directory.

        Example:
            >>> get_config().templates_dir.name  # doctest: +SKIP
            'templates'
        """
        return self._path.parent.parent.parent / "templates"

    # ── Specs paths ───────────────────────────────────────────────

    @property
    def product_vision_file_path(self) -> str:
        """Path to the project's product-vision markdown file.

        Example:
            >>> get_config().product_vision_file_path  # doctest: +SKIP
            'docs/product-vision.md'
        """
        return self._paths().get("product_vision_file", "")

    @property
    def decisions_file_path(self) -> str:
        """Path to the architecture-decisions log file.

        Example:
            >>> get_config().decisions_file_path  # doctest: +SKIP
            'docs/decisions.md'
        """
        return self._paths().get("decisions_file", "")

    @property
    def architecture_file_path(self) -> str:
        """Path to the project's architecture markdown file.

        Example:
            >>> get_config().architecture_file_path  # doctest: +SKIP
            'docs/architecture.md'
        """
        return self._paths().get("architecture_file", "")

    @property
    def backlog_md_file_path(self) -> str:
        """Path to the human-edited backlog markdown file.

        Example:
            >>> get_config().backlog_md_file_path  # doctest: +SKIP
            'docs/backlog.md'
        """
        return self._paths().get("backlog_md_file", "")

    @property
    def backlog_json_file_path(self) -> str:
        """Path to the machine-generated backlog JSON file.

        Example:
            >>> get_config().backlog_json_file_path  # doctest: +SKIP
            '.claude/backlog.json'
        """
        return self._paths().get("backlog_json_file", "")

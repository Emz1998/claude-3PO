"""extractors — Pure extraction helpers for hook payloads and markdown text.

Split into domain sub-modules; this package-level ``__init__`` re-exports
every public name so existing ``from lib.extractors import X`` imports keep
working unchanged.

Sub-modules:
    * :mod:`lib.extractors.hooks` — skill/agent name parsing from hook payloads.
    * :mod:`lib.extractors.review` — reviewer scores and Pass/Fail verdicts.
    * :mod:`lib.extractors.markdown` — sections, tables, bullets, bold metadata.
    * :mod:`lib.extractors.plans` — plan-file dependencies / tasks / file tables.
    * :mod:`lib.extractors.commands` — ``/build`` prompt and ``gh pr checks`` parsers.
"""

from .hooks import (
    strip_namespace,
    extract_skill_name,
    extract_agent_name,
)
from .review import (
    extract_scores,
    extract_verdict,
)
from .markdown import (
    extract_md_sections,
    extract_table,
    extract_bullet_items,
    match_substring,
    validate_bullet_section,
    require_section,
    extract_section_map,
    extract_md_body,
    extract_frontmatter,
    extract_bold_metadata,
)
from .plans import (
    extract_plan_dependencies,
    extract_plan_tasks,
    extract_plan_files_to_modify,
)
from .commands import (
    extract_build_instructions,
    extract_ci_status,
)

__all__ = [
    # hooks
    "strip_namespace",
    "extract_skill_name",
    "extract_agent_name",
    # review
    "extract_scores",
    "extract_verdict",
    # markdown
    "extract_md_sections",
    "extract_table",
    "extract_bullet_items",
    "match_substring",
    "validate_bullet_section",
    "require_section",
    "extract_section_map",
    "extract_md_body",
    "extract_frontmatter",
    "extract_bold_metadata",
    # plans
    "extract_plan_dependencies",
    "extract_plan_tasks",
    "extract_plan_files_to_modify",
    # commands
    "extract_build_instructions",
    "extract_ci_status",
]

"""SpecsValidator — single validator for architecture, constitution,
product-vision, and backlog markdown + their JSON forms.

Schemas are derived from the canonical template markdown files via
utils.template_schema.TemplateSchema. Doc-grammar constants (markers,
regexes) live in constants.SPECS_* . This module only orchestrates
the checks.
"""

from __future__ import annotations

import re
from typing import Any

from constants import (
    SPECS_AC_MARKERS,
    SPECS_BLOCKQUOTE_PATTERNS,
    SPECS_FIELD_MARKERS,
    SPECS_ID_REGEX_TEMPLATE,
    SPECS_PLACEHOLDER_PREFIXES,
    SPECS_STORIES_HEADING,
)
from lib.extractors import extract_bold_metadata, extract_md_sections
from utils.template_schema import TemplateSchema


_TEMPLATE_FILENAMES = {
    "architecture": "architecture.md",
    "constitution": "constitution.md",
    "product_vision": "product-vision.md",
    "backlog": "backlog.md",
}


class SpecsValidator:
    """Validates specs markdown and converts backlog markdown → JSON."""

    def __init__(self, config):
        self.config = config
        self._schema_cache: dict[str, TemplateSchema] = {}

    def _schema(self, doc_type: str) -> TemplateSchema:
        cached = self._schema_cache.get(doc_type)
        if cached is not None:
            return cached
        filename = _TEMPLATE_FILENAMES.get(doc_type)
        if filename is None:
            schema = TemplateSchema()
        else:
            schema = TemplateSchema.from_file(
                self.config.templates_dir / filename, doc_type
            )
        self._schema_cache[doc_type] = schema
        return schema

    # ── Per-doc entry points ──────────────────────────────────────

    def validate_architecture(self, content: str) -> list[str]:
        schema = self._schema("architecture")
        errors = self._check_bold_metadata(
            content,
            schema.metadata_fields,
            status_field="Status",
            valid_statuses=schema.status_enums.get("Status", []),
        )
        errors += self._check_required_sections(
            content,
            schema.required_sections,
            level=2,
            allowed_extras=schema.allowed_extra_sections,
        )
        errors += self._check_required_subsections(
            content, schema.required_subsections
        )
        return errors

    def validate_constitution(self, content: str) -> list[str]:
        schema = self._schema("constitution")
        errors = self._check_bold_metadata(content, schema.metadata_fields)
        errors += self._check_required_sections(
            content,
            schema.required_sections,
            level=1,
            skip_titles=[schema.doc_title],
            flag_unknown=False,
        )
        errors += self._check_required_subsections(
            content,
            schema.required_subsections,
            parent_level=1,
            child_level=2,
        )
        errors += self._check_required_subsections(
            content,
            schema.required_h3_subsections,
            parent_level=2,
            child_level=3,
        )
        errors += self._check_governing_principles(content, minimum=4)
        errors += self._check_dod_checklists(content)
        errors += self._check_tooling_table(content)
        return errors

    @staticmethod
    def _check_governing_principles(content: str, *, minimum: int) -> list[str]:
        count = SpecsValidator._count_numbered_bold_principles(content)
        if count == 0:
            return ["governing_principles: no numbered principles found"]
        if count < minimum:
            return [f"governing_principles: found {count} principles, minimum is {minimum}"]
        return []

    @staticmethod
    def _count_numbered_bold_principles(content: str) -> int:
        in_section = False
        count = 0
        for line in content.splitlines():
            if line.startswith("# Governing Principles"):
                in_section = True
                continue
            if in_section and line.startswith("# ") and not line.startswith("## "):
                break
            if in_section and re.match(r"^\d+\.\s+\*\*", line):
                count += 1
        return count

    @staticmethod
    def _check_dod_checklists(content: str) -> list[str]:
        dod_sections = ("Task Done", "Story Done", "Sprint Done")
        counts = {name: 0 for name in dod_sections}
        current = ""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                heading = stripped[3:].strip()
                current = heading if heading in dod_sections else ""
            elif current and any(stripped.startswith(m) for m in SPECS_AC_MARKERS):
                counts[current] += 1
        return [
            f"definition_of_done.{section}: no checklist items found"
            for section, n in counts.items() if n == 0
        ]

    @staticmethod
    def _check_tooling_table(content: str) -> list[str]:
        if re.search(r"\|\s*Tool\s*\|", content):
            return []
        return ["tooling: tooling table not found (expected '| Tool |' header)"]

    def validate_product_vision(self, content: str) -> list[str]:
        schema = self._schema("product_vision")
        errors = self._check_bold_metadata(content, schema.metadata_fields)
        errors += self._check_required_sections(
            content, schema.required_sections
        )
        errors += self._check_required_subsections(
            content, schema.required_subsections
        )
        errors += self._check_required_tables(content, schema.required_tables)
        return errors

    def validate_backlog_md(self, content: str) -> list[str]:
        schema = self._schema("backlog")
        errors = self._check_bold_metadata(content, schema.metadata_fields)
        errors += self._check_backlog_sections(content, schema.required_sections)
        items = self._parse_story_items(content)
        if not items:
            errors.append("stories: no story sections found")
            return errors
        for item in items:
            errors += self._validate_backlog_item(item, schema)
        return errors

    @staticmethod
    def _check_backlog_sections(content: str, valid: list[str]) -> list[str]:
        allowed = set(valid)
        return [
            f"structure: unknown section '## {section}'"
            for section in SpecsValidator._headings_at_level(content, 2)
            if section not in allowed
        ]

    def _validate_backlog_item(
        self, item: dict[str, Any], schema: TemplateSchema
    ) -> list[str]:
        sid = item["id"]
        prefix = sid.split("-")[0] if "-" in sid else ""
        pfx = f"stories.{sid}"
        errors: list[str] = []
        errors += self._validate_item_id(sid, prefix, pfx, schema.valid_item_types)
        errors += self._validate_item_fields(item, pfx, schema.valid_priorities)
        errors += self._validate_item_blockquote(item, prefix, pfx)
        return errors

    @staticmethod
    def _validate_item_id(
        sid: str, prefix: str, pfx: str, valid_types: list[str]
    ) -> list[str]:
        if prefix not in valid_types:
            return [f"{pfx}.id: prefix '{prefix}' not in {set(valid_types)}"]
        pattern = SPECS_ID_REGEX_TEMPLATE.format(prefix=prefix)
        if not re.match(pattern, sid):
            return [f"{pfx}.id: '{sid}' doesn't match pattern for '{prefix}'"]
        return []

    @staticmethod
    def _validate_item_fields(
        item: dict[str, Any], pfx: str, valid_priorities: list[str]
    ) -> list[str]:
        errors: list[str] = []
        if not item["title"]:
            errors.append(f"{pfx}.title: is empty")
        if not item["description"]:
            errors.append(f"{pfx}.description: is empty")
        priority = item["priority"]
        if not priority:
            errors.append(f"{pfx}: missing **Priority:** field")
        elif priority not in valid_priorities:
            errors.append(f"{pfx}.priority: '{priority}' not in {set(valid_priorities)}")
        if not item["acceptance_criteria"]:
            errors.append(f"{pfx}.acceptance_criteria: no criteria listed")
        return errors

    @staticmethod
    def _validate_item_blockquote(
        item: dict[str, Any], prefix: str, pfx: str
    ) -> list[str]:
        pattern = SPECS_BLOCKQUOTE_PATTERNS.get(prefix)
        if not pattern:
            return []
        bq_text = " ".join(item.get("blockquotes", []))
        if re.search(pattern, bq_text):
            return []
        hint = {
            "US": "'> **As a** [role], **I want** [what] **so that** [why]'",
            "TS": "'> **As a** [dev/system], **I need** [what] **so that** [why]'",
            "SK": "'> **Investigate:** [what]' and '> **To decide:** [what]'",
            "BG": "'> **What\\'s broken:** [x]', '> **Expected:** [x]', '> **Actual:** [x]'",
        }[prefix]
        return [f"{pfx}.format: {prefix} stories must have {hint}"]

    def validate_backlog_json(self, data: dict[str, Any]) -> list[str]:
        schema = self._schema("backlog")
        errors = _check_json_root(data)
        stories = data.get("stories") if isinstance(data, dict) else None
        if isinstance(stories, list):
            for i, story in enumerate(stories):
                prefix = f"stories[{i}]"
                if not isinstance(story, dict):
                    errors.append(
                        f"{prefix}: expected object, got {type(story).__name__}"
                    )
                    continue
                errors += self._validate_backlog_story_json(story, prefix, schema)
        return errors

    def _validate_backlog_story_json(
        self, story: dict[str, Any], prefix: str, schema: TemplateSchema
    ) -> list[str]:
        errors = _check_story_json_fields(story, prefix)
        errors += _check_story_item_type(story, prefix)
        errors += self._check_story_type_and_id(story, prefix, schema)
        errors += self._check_story_enum_values(story, prefix, schema)
        return errors

    def _check_story_type_and_id(
        self, story: dict[str, Any], prefix: str, schema: TemplateSchema
    ) -> list[str]:
        type_names = schema.story_type_names
        long_to_prefix = {long: short for short, long in type_names.items()}
        valid_long = set(long_to_prefix)
        story_type = story.get("type")
        errors: list[str] = []
        if not isinstance(story_type, str):
            return errors
        if story_type not in valid_long:
            errors.append(f"{prefix}.type: '{story_type}' not in {valid_long}")
        prefix_code = long_to_prefix.get(story_type, "")
        sid = story.get("id", "")
        if prefix_code and isinstance(sid, str):
            pattern = SPECS_ID_REGEX_TEMPLATE.format(prefix=prefix_code)
            if not re.match(pattern, sid):
                errors.append(
                    f"{prefix}.id: '{sid}' does not match pattern for '{story_type}'"
                )
        return errors

    @staticmethod
    def _check_story_enum_values(
        story: dict[str, Any], prefix: str, schema: TemplateSchema
    ) -> list[str]:
        errors: list[str] = []
        valid_statuses = set(schema.json_item_statuses)
        valid_priorities = set(schema.valid_priorities)
        status = story.get("status")
        if isinstance(status, str) and status not in valid_statuses:
            errors.append(f"{prefix}.status: '{status}' not in {valid_statuses}")
        priority = story.get("priority")
        if isinstance(priority, str) and priority not in valid_priorities:
            errors.append(f"{prefix}.priority: '{priority}' not in {valid_priorities}")
        for field in ("start_date", "target_date"):
            val = story.get(field)
            if isinstance(val, str) and val and not re.match(_DATE_PATTERN, val):
                errors.append(f"{prefix}.{field}: must be YYYY-MM-DD, got '{val}'")
        return errors

    # ── Converters ────────────────────────────────────────────────

    def convert_backlog_md_to_json(self, content: str) -> dict[str, Any]:
        meta = extract_bold_metadata(content)
        type_names = self._schema("backlog").story_type_names
        items = self._parse_story_items(content)
        stories = [self._story_to_json(item, type_names) for item in items]
        return {
            "project": meta.get("Project", ""),
            "goal": meta.get("Goal", ""),
            "dates": {"start": "", "end": ""},
            "totalPoints": 0,
            "stories": stories,
        }

    @staticmethod
    def _story_to_json(
        item: dict[str, Any], type_names: dict[str, str]
    ) -> dict[str, Any]:
        sid = item["id"]
        prefix = sid.split("-")[0] if "-" in sid else ""
        return {
            "id": sid,
            "type": type_names.get(prefix, "User Story"),
            "title": item["title"],
            "description": item["description"],
            "status": "Backlog",
            "priority": item["priority"],
            "is_blocking": SpecsValidator._parse_list_field(item["is_blocking"]),
            "blocked_by": SpecsValidator._parse_list_field(item["blocked_by"]),
            "acceptance_criteria": [
                SpecsValidator._strip_ac_marker(c) for c in item["acceptance_criteria"]
            ],
            "item_type": "story",
            "milestone": item["milestone"],
            "start_date": "",
            "target_date": "",
        }

    @staticmethod
    def _parse_list_field(raw: str) -> list[str]:
        raw = raw.strip().strip("`").strip("[").strip("]")
        placeholder = {"", "none", "-", "none / sk-nnn", "none / ts-nnn, us-nnn"}
        if raw.lower() in placeholder:
            return []
        return [v.strip() for v in raw.split(",") if v.strip() and v.strip().lower() != "none"]

    @staticmethod
    def _strip_ac_marker(line: str) -> str:
        return re.sub(r"^- \[[ x]\] ", "", line).strip("`")

    # ── Shared helpers ────────────────────────────────────────────

    @staticmethod
    def _is_placeholder(value: str) -> bool:
        return not value or any(value.startswith(p) for p in SPECS_PLACEHOLDER_PREFIXES)

    def _check_bold_metadata(
        self,
        content: str,
        required_fields: list[str],
        *,
        status_field: str | None = None,
        valid_statuses: list[str] | None = None,
    ) -> list[str]:
        """Report missing, placeholder, or invalid-status metadata fields."""
        meta = extract_bold_metadata(content)
        errors: list[str] = []
        for label in required_fields:
            if label not in meta:
                errors.append(f"metadata: missing required field '{label}'")
                continue
            if self._is_placeholder(meta[label]):
                errors.append(f"metadata.{label}: field is empty or placeholder")
        if status_field and valid_statuses:
            status = meta.get(status_field, "")
            if status and "/" not in status and status not in valid_statuses:
                errors.append(f"metadata.{status_field}: '{status}' not in {set(valid_statuses)}")
        return errors

    @staticmethod
    def _headings_at_level(content: str, level: int) -> list[str]:
        return [name for name, _ in extract_md_sections(content, level)]

    def _check_required_sections(
        self,
        content: str,
        required: list[str],
        *,
        level: int = 2,
        allowed_extras: list[str] | None = None,
        flag_unknown: bool = True,
        skip_titles: list[str] | None = None,
    ) -> list[str]:
        """Check all required H<level> sections are present; optionally flag unknowns."""
        found = set(self._headings_at_level(content, level))
        errors = [
            f"structure: missing required section '{'#' * level} {req}'"
            for req in required
            if req not in found
        ]
        if not flag_unknown:
            return errors
        allowed = set(required) | set(allowed_extras or []) | set(skip_titles or [])
        for section in found:
            if section in (skip_titles or []):
                continue
            if section not in allowed:
                errors.append(f"structure: unknown section '{'#' * level} {section}'")
        return errors

    def _check_required_subsections(
        self,
        content: str,
        required: dict[str, list[str]],
        *,
        parent_level: int = 2,
        child_level: int = 3,
    ) -> list[str]:
        """Check each parent section contains its required child-level subsections."""
        found = self._collect_subsections(content, parent_level, child_level)
        errors: list[str] = []
        for parent, subs in required.items():
            present = found.get(parent, set())
            for sub in subs:
                if sub not in present:
                    errors.append(
                        f"structure.{parent}: missing subsection "
                        f"'{'#' * child_level} {sub}'"
                    )
        return errors

    @staticmethod
    def _collect_subsections(
        content: str, parent_level: int, child_level: int
    ) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for parent, body in extract_md_sections(content, parent_level):
            children = {name for name, _ in extract_md_sections(body, child_level)}
            out[parent] = children
        return out

    def _check_required_tables(
        self, content: str, table_specs: list[dict[str, str]]
    ) -> list[str]:
        """Each spec declares a section label + a required column header that must appear."""
        errors: list[str] = []
        for spec in table_specs:
            header = spec.get("required_header", "")
            if not header:
                continue
            pattern = rf"\|\s*{re.escape(header)}\s*\|"
            if not re.search(pattern, content):
                errors.append(
                    f"table.{spec.get('section', header)}: table not found or "
                    f"missing header '{header}'"
                )
        return errors

    # ── Story / task item parsing (backlog) ───────────────────────

    @staticmethod
    def _parse_story_items(content: str) -> list[dict[str, Any]]:
        """Parse `### ID: Title` items under the `## Stories` section."""
        lines = content.split("\n")
        start = SpecsValidator._find_stories_section(lines)
        if start < 0:
            return []
        items: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for i in range(start + 1, len(lines)):
            match = re.match(r"^### ([\w-]+):\s*(.*)$", lines[i])
            if match:
                if current:
                    items.append(current)
                current = SpecsValidator._new_item(
                    match.group(1),
                    match.group(2).strip().strip("`"),
                    i + 1,
                )
                continue
            if current:
                SpecsValidator._parse_item_line(current, lines[i].strip())
        if current:
            items.append(current)
        return items

    @staticmethod
    def _find_stories_section(lines: list[str]) -> int:
        target = f"## {SPECS_STORIES_HEADING}"
        for i, line in enumerate(lines):
            if line.strip() == target:
                return i
        return -1

    @staticmethod
    def _new_item(sid: str, title: str, line_num: int) -> dict[str, Any]:
        return {
            "id": sid,
            "title": title,
            "line": line_num,
            "description": "",
            "priority": "",
            "milestone": "",
            "is_blocking": "",
            "blocked_by": "",
            "acceptance_criteria": [],
            "blockquotes": [],
        }

    @staticmethod
    def _parse_item_line(item: dict[str, Any], stripped: str) -> None:
        if stripped.startswith(">"):
            item["blockquotes"].append(stripped)
            return
        for field, marker in SPECS_FIELD_MARKERS.items():
            if stripped.startswith(marker) and field in item:
                item[field] = stripped.split(marker, 1)[1].strip().strip("`")
                return
        if any(stripped.startswith(m) for m in SPECS_AC_MARKERS):
            item["acceptance_criteria"].append(stripped)


_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def _require_field(
    obj: dict, field: str, expected_type: type, prefix: str, errors: list[str]
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], expected_type):
        errors.append(
            f"{prefix}.{field}: expected {expected_type.__name__}, "
            f"got {type(obj[field]).__name__}"
        )


def _require_list_field(
    obj: dict, field: str, item_type: type, prefix: str, errors: list[str]
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], list):
        errors.append(f"{prefix}.{field}: expected array")
    elif not all(isinstance(v, item_type) for v in obj[field]):
        errors.append(f"{prefix}.{field}: all entries must be {item_type.__name__}")


def _check_json_root(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_field(data, "project", str, "root", errors)
    _require_field(data, "goal", str, "root", errors)
    errors += _check_json_dates(data)
    if "totalPoints" not in data:
        errors.append("root: missing required field 'totalPoints'")
    elif not isinstance(data["totalPoints"], int):
        errors.append(
            f"root.totalPoints: expected int, got {type(data['totalPoints']).__name__}"
        )
    if "stories" not in data:
        errors.append("root: missing required field 'stories'")
    elif not isinstance(data["stories"], list):
        errors.append("root.stories: expected array")
    return errors


def _check_json_dates(data: dict[str, Any]) -> list[str]:
    if "dates" not in data:
        return ["root: missing required field 'dates'"]
    dates = data["dates"]
    if not isinstance(dates, dict):
        return ["root.dates: expected object"]
    errors: list[str] = []
    for field in ("start", "end"):
        val = dates.get(field)
        if val is None:
            errors.append(f"root.dates: missing required field '{field}'")
        elif not isinstance(val, str):
            errors.append(
                f"root.dates.{field}: expected string, got {type(val).__name__}"
            )
        elif val and not re.match(_DATE_PATTERN, val):
            errors.append(f"root.dates.{field}: must be YYYY-MM-DD, got '{val}'")
    return errors


def _check_story_json_fields(story: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for field in (
        "id", "type", "title", "description", "status",
        "priority", "milestone", "start_date", "target_date",
    ):
        _require_field(story, field, str, prefix, errors)
    for field in ("is_blocking", "blocked_by", "acceptance_criteria"):
        _require_list_field(story, field, str, prefix, errors)
    return errors


def _check_story_item_type(story: dict[str, Any], prefix: str) -> list[str]:
    if "item_type" not in story:
        return [f"{prefix}: missing required field 'item_type'"]
    if story["item_type"] != "story":
        return [f"{prefix}.item_type: must be 'story', got '{story['item_type']}'"]
    return []


# Backwards-compatible module-level entry points (used by utils/specs_writer.py).

def _default_validator() -> SpecsValidator:
    from config import Config
    return SpecsValidator(Config())


def validate_architecture(content: str) -> list[str]:
    return _default_validator().validate_architecture(content)


def validate_backlog_md(content: str) -> list[str]:
    return _default_validator().validate_backlog_md(content)


def convert_backlog_md_to_json(content: str) -> dict[str, Any]:
    return _default_validator().convert_backlog_md_to_json(content)

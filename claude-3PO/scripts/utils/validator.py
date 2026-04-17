"""SpecsValidator — single validator for architecture, constitution,
product-vision, backlog, and sprint markdown + their JSON forms.

Schemas live in config.specs_schemas; doc-grammar constants live in
constants.SPECS_* . This module only orchestrates the checks.
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
from lib.extractors import (
    extract_bold_metadata,
    extract_md_sections,
    extract_table,
)


class SpecsValidator:
    """Validates specs markdown and converts markdown → JSON for backlog/sprint."""

    def __init__(self, config):
        self.config = config

    # ── Per-doc entry points ──────────────────────────────────────

    def validate_architecture(self, content: str) -> list[str]:
        errors = self._check_bold_metadata(
            content,
            self.config.specs_metadata_fields("architecture"),
            status_field="Status",
            valid_statuses=self.config.specs_valid_statuses("architecture"),
        )
        errors += self._check_required_sections(
            content,
            self.config.specs_required_sections("architecture"),
            level=2,
            allowed_extras=self.config.specs_allowed_extra_sections("architecture"),
        )
        errors += self._check_required_subsections(
            content,
            self.config.specs_required_subsections("architecture"),
        )
        return errors

    def validate_constitution(self, content: str) -> list[str]:
        schema = self.config.specs_schema("constitution")
        errors = self._check_bold_metadata(content, schema.get("metadata_fields", []))
        errors += self._check_required_sections(
            content,
            schema.get("required_h1_sections", []),
            level=1,
            allowed_extras=schema.get("optional_h2_sections", []),
            skip_titles=[schema.get("doc_title", "")],
        )
        errors += self._check_required_subsections(
            content,
            schema.get("required_h2_sections", {}),
            parent_level=1,
            child_level=2,
        )
        errors += self._check_required_subsections(
            content,
            schema.get("required_h3_subsections", {}),
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
        errors = self._check_bold_metadata(
            content, self.config.specs_metadata_fields("product_vision")
        )
        errors += self._check_required_sections(
            content,
            self.config.specs_required_sections("product_vision"),
        )
        errors += self._check_required_subsections(
            content,
            self.config.specs_required_subsections("product_vision"),
        )
        errors += self._check_required_tables(
            content, self.config.specs_required_tables("product_vision")
        )
        return errors

    def validate_backlog_md(self, content: str) -> list[str]:
        schema = self.config.specs_schema("backlog")
        errors = self._check_bold_metadata(content, schema.get("metadata_fields", []))
        errors += self._check_backlog_sections(content, schema.get("valid_sections", []))
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
        self, item: dict[str, Any], schema: dict[str, Any]
    ) -> list[str]:
        sid = item["id"]
        prefix = sid.split("-")[0] if "-" in sid else ""
        pfx = f"stories.{sid}"
        errors: list[str] = []
        errors += self._validate_item_id(sid, prefix, pfx, schema.get("valid_item_types", []))
        errors += self._validate_item_fields(item, pfx, schema.get("valid_priorities", []))
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
        schema = self.config.specs_schema("backlog")
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
        self, story: dict[str, Any], prefix: str, schema: dict[str, Any]
    ) -> list[str]:
        errors = _check_story_json_fields(story, prefix)
        errors += _check_story_item_type(story, prefix)
        errors += self._check_story_type_and_id(story, prefix, schema)
        errors += self._check_story_enum_values(story, prefix, schema)
        return errors

    def _check_story_type_and_id(
        self, story: dict[str, Any], prefix: str, schema: dict[str, Any]
    ) -> list[str]:
        type_names = schema.get("story_type_names", {})
        long_to_prefix = {long: short for short, long in type_names.items()}
        valid_long = set(long_to_prefix)
        story_type = story.get("type")
        errors: list[str] = []
        if isinstance(story_type, str) and story_type not in valid_long:
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
        story: dict[str, Any], prefix: str, schema: dict[str, Any]
    ) -> list[str]:
        errors: list[str] = []
        valid_statuses = set(schema.get("json_item_statuses", []))
        valid_priorities = set(schema.get("valid_priorities", []))
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

    def validate_sprint_md(self, content: str) -> list[str]:
        schema = self.config.specs_schema("sprint")
        return _sprint_md_validate(content, schema)

    def validate_sprint_json(self, data: dict[str, Any]) -> list[str]:
        schema = self.config.specs_schema("sprint")
        return _sprint_json_validate(data, schema)

    # ── Converters ────────────────────────────────────────────────

    def convert_backlog_md_to_json(self, content: str) -> dict[str, Any]:
        meta = extract_bold_metadata(content)
        type_names = self.config.specs_story_type_names("backlog")
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

    def convert_sprint_md_to_json(self, content: str) -> dict[str, Any]:
        return _sprint_md_to_json(content)

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
        prefix = "#" * level + " "
        exclude = "#" * (level + 1) + " "
        return [
            line[len(prefix):].strip()
            for line in content.splitlines()
            if line.startswith(prefix) and not line.startswith(exclude)
        ]

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
        parent_prefix = "#" * parent_level + " "
        child_prefix = "#" * child_level + " "
        excluded_parent = "#" * (parent_level + 1) + " "
        excluded_child = "#" * (child_level + 1) + " "
        current = ""
        out: dict[str, set[str]] = {}
        for line in content.splitlines():
            if line.startswith(parent_prefix) and not line.startswith(excluded_parent):
                current = line[len(parent_prefix):].strip()
                out.setdefault(current, set())
            elif line.startswith(child_prefix) and not line.startswith(excluded_child) and current:
                out[current].add(line[len(child_prefix):].strip())
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

    # ── Story / task item parsing (backlog + sprint) ──────────────

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


# ──────────────────────────────────────────────────────────────────
# Sprint MD validator
# ──────────────────────────────────────────────────────────────────


def _sprint_md_validate(content: str, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")
    _sprint_md_check_metadata(lines, schema, errors)
    items = _sprint_md_check_table(lines, schema, errors)
    _sprint_md_check_details(content, items, schema, errors)
    return errors


def _sprint_md_check_metadata(
    lines: list[str], schema: dict[str, Any], errors: list[str]
) -> None:
    meta = extract_bold_metadata("\n".join(lines))
    for label in schema.get("metadata_fields", []):
        if label not in meta:
            errors.append(f"metadata: missing required field '{label}'")
            continue
        value = meta[label]
        if not value:
            errors.append(f"metadata.{label}: field is empty")
    sprint_num = meta.get("Sprint #", "")
    if sprint_num and not sprint_num.lstrip("-").isdigit():
        errors.append(f"metadata.Sprint #: must be a number, got '{sprint_num}'")
    due = meta.get("Due Date", "")
    if due and not re.match(_DATE_PATTERN, due):
        errors.append(f"metadata.Due Date: must be YYYY-MM-DD, got '{due}'")


def _sprint_md_check_table(
    lines: list[str], schema: dict[str, Any], errors: list[str]
) -> list[dict[str, str]]:
    header_idx = next((i for i, ln in enumerate(lines) if ln.startswith("| ID")), -1)
    if header_idx < 0:
        errors.append("table: overview table not found (expected '| ID' header row)")
        return []
    headers = [h.strip() for h in lines[header_idx].split("|")[1:-1]]
    for req in schema.get("overview_table_headers", []):
        if req not in headers:
            errors.append(f"table.header: missing required column '{req}'")
    return _sprint_md_parse_table_rows(lines, header_idx + 2, schema, errors)


def _sprint_md_parse_table_rows(
    lines: list[str], start: int, schema: dict[str, Any], errors: list[str]
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for i in range(start, len(lines)):
        if not lines[i].startswith("|"):
            break
        cols = [c.strip() for c in lines[i].split("|")[1:-1]]
        if len(cols) < 6:
            errors.append(f"table.row[{i}]: expected at least 6 columns, got {len(cols)}")
            continue
        _sprint_md_check_row_values(cols, schema, errors)
        items.append({"id": cols[0], "type": cols[1]})
    if not items:
        errors.append("table: no data rows found")
    return items


def _sprint_md_check_row_values(
    cols: list[str], schema: dict[str, Any], errors: list[str]
) -> None:
    item_id, item_type, title, points, status = cols[:5]
    prefix = f"table.{item_id}"
    _enum_check(item_type, schema.get("valid_story_types", []), prefix, "type", errors)
    id_prefixes = schema.get("story_id_prefixes", {})
    id_prefix = id_prefixes.get(item_type)
    if id_prefix:
        pattern = SPECS_ID_REGEX_TEMPLATE.format(prefix=id_prefix)
        if not re.match(pattern, item_id):
            errors.append(f"{prefix}.id: '{item_id}' doesn't match pattern for '{item_type}'")
    if not title:
        errors.append(f"{prefix}.title: is empty")
    if points and not points.lstrip("-").isdigit():
        errors.append(f"{prefix}.points: must be a number, got '{points}'")
    _enum_check(status, schema.get("valid_story_statuses", []), prefix, "status", errors)


def _enum_check(
    value: str, valid: list[str], prefix: str, field: str, errors: list[str]
) -> None:
    if value and value not in valid:
        errors.append(f"{prefix}.{field}: '{value}' not in {set(valid)}")


def _sprint_md_check_details(
    content: str, items: list[dict[str, str]], schema: dict[str, Any], errors: list[str]
) -> None:
    for item in items:
        item_id = item["id"]
        pfx = f"detail.{item_id}"
        block = _sprint_md_extract_detail(content, item_id, pfx, errors)
        if block is not None:
            _sprint_md_check_story_block(block, pfx, schema, errors)


def _sprint_md_extract_detail(
    content: str, item_id: str, pfx: str, errors: list[str]
) -> str | None:
    pattern = rf"#### {re.escape(item_id)}:"
    if not re.search(pattern, content):
        errors.append(f"{pfx}: missing detail section (expected '#### {item_id}: ...')")
        return None
    block_pattern = (
        rf"#### {re.escape(item_id)}:.*?\n(.*?)"
        r"(?=\n---|\n#### [A-Z]{2,}-\d|\Z)"
    )
    match = re.search(block_pattern, content, re.DOTALL)
    return match.group(1) if match else None


def _sprint_md_check_story_block(
    block: str, pfx: str, schema: dict[str, Any], errors: list[str]
) -> None:
    for field in ("Labels", "Points", "Status", "TDD", "Priority", "Is Blocking", "Blocked By"):
        if not _sprint_parse_field(block, field):
            errors.append(f"{pfx}: missing **{field}:**")
    _enum_check(_sprint_parse_field(block, "Status"), schema.get("valid_story_statuses", []), pfx, "status", errors)
    _enum_check(_sprint_parse_field(block, "Priority"), schema.get("valid_priorities", []), pfx, "priority", errors)
    tdd = _sprint_parse_field(block, "TDD").lower()
    if tdd and tdd not in ("true", "false"):
        errors.append(f"{pfx}.tdd: must be 'true' or 'false', got '{tdd}'")
    for field in ("Start Date", "Target Date"):
        val = _sprint_parse_field(block, field)
        if val and val != "empty" and not re.match(_DATE_PATTERN, val):
            errors.append(f"{pfx}.{field}: must be YYYY-MM-DD, got '{val}'")
    if not re.search(r"\*\*Acceptance Criteria", block):
        errors.append(f"{pfx}: missing **Acceptance Criteria:** section")
    _sprint_md_check_tasks(block, pfx, schema, errors)


def _sprint_parse_field(block: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else ""


def _sprint_md_check_tasks(
    block: str, pfx: str, schema: dict[str, Any], errors: list[str]
) -> None:
    task_ids = re.findall(r"- \*\*T-(\d+):\*\*", block)
    if not task_ids:
        errors.append(f"{pfx}: no tasks found (expected '- **T-NNN:** ...')")
        return
    for task_num in task_ids:
        task_id = f"T-{task_num}"
        tblock = _sprint_md_extract_task(block, task_id)
        if tblock is not None:
            _sprint_md_check_task_block(tblock, f"{pfx}.{task_id}", schema, errors)


def _sprint_md_extract_task(block: str, task_id: str) -> str | None:
    pattern = (
        rf"- \*\*{re.escape(task_id)}:\*\*(.*?)"
        r"(?=\n- \*\*T-\d+:\*\*|\n---|\n####|\Z)"
    )
    match = re.search(pattern, block, re.DOTALL)
    return match.group(1) if match else None


def _sprint_md_check_task_block(
    block: str, pfx: str, schema: dict[str, Any], errors: list[str]
) -> None:
    for field in ("Description", "Status", "Priority", "Complexity", "Labels", "Blocked by"):
        if not _sprint_parse_field(block, field):
            errors.append(f"{pfx}: missing **{field}:**")
    _enum_check(_sprint_parse_field(block, "Status"), schema.get("valid_task_statuses", []), pfx, "status", errors)
    _enum_check(_sprint_parse_field(block, "Priority"), schema.get("valid_priorities", []), pfx, "priority", errors)
    _enum_check(_sprint_parse_field(block, "Complexity"), schema.get("valid_complexities", []), pfx, "complexity", errors)
    for field in ("Start date", "Target date"):
        val = _sprint_parse_field(block, field)
        if val and val != "empty" and not re.match(_DATE_PATTERN, val):
            errors.append(f"{pfx}.{field}: must be YYYY-MM-DD, got '{val}'")
    if not re.findall(r"- \[[ x]\] (.+)", block):
        errors.append(f"{pfx}: no acceptance criteria checklist items found")


# ──────────────────────────────────────────────────────────────────
# Sprint JSON validator
# ──────────────────────────────────────────────────────────────────


def _sprint_json_validate(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _sprint_json_check_root(data, errors)
    stories = data.get("stories") if isinstance(data, dict) else None
    if not isinstance(stories, list):
        return errors
    task_ids = _sprint_json_collect_task_ids(stories)
    for i, story in enumerate(stories):
        pfx = f"stories[{i}]"
        if not isinstance(story, dict):
            errors.append(f"{pfx}: expected object, got {type(story).__name__}")
            continue
        _sprint_json_check_story(story, pfx, schema, errors, task_ids)
    return errors


def _sprint_json_collect_task_ids(stories: list[Any]) -> set[str]:
    ids: set[str] = set()
    for s in stories:
        if not isinstance(s, dict):
            continue
        for t in s.get("tasks", []) or []:
            if isinstance(t, dict) and isinstance(t.get("id"), str):
                ids.add(t["id"])
    return ids


def _sprint_json_check_root(data: dict[str, Any], errors: list[str]) -> None:
    _require_field(data, "sprint", int, "root", errors)
    _require_field(data, "milestone", str, "root", errors)
    _require_field(data, "description", str, "root", errors)
    _require_field(data, "due_date", str, "root", errors)
    due = data.get("due_date")
    if isinstance(due, str) and due and not re.match(_DATE_PATTERN, due):
        errors.append(f"root.due_date: must be YYYY-MM-DD, got '{due}'")
    if "stories" not in data:
        errors.append("root: missing required field 'stories'")
    elif not isinstance(data["stories"], list):
        errors.append("root.stories: expected array")


def _sprint_json_check_story(
    story: dict[str, Any], pfx: str, schema: dict[str, Any],
    errors: list[str], task_ids: set[str],
) -> None:
    _sprint_json_check_story_fields(story, pfx, errors)
    _sprint_json_check_item_type(story, pfx, "story", errors)
    _sprint_json_check_story_values(story, pfx, schema, errors)
    tasks = story.get("tasks")
    if "tasks" not in story:
        errors.append(f"{pfx}: missing required field 'tasks'")
    elif not isinstance(tasks, list):
        errors.append(f"{pfx}.tasks: expected array")
    else:
        for j, task in enumerate(tasks):
            tp = f"{pfx}.tasks[{j}]"
            if not isinstance(task, dict):
                errors.append(f"{tp}: expected object")
                continue
            _sprint_json_check_task(task, tp, schema, errors, task_ids)


def _sprint_json_check_story_fields(
    story: dict[str, Any], pfx: str, errors: list[str]
) -> None:
    for field, typ in (
        ("id", str), ("type", str), ("title", str), ("description", str),
        ("points", int), ("status", str), ("tdd", bool), ("priority", str),
        ("milestone", str), ("start_date", str), ("target_date", str),
    ):
        _require_field(story, field, typ, pfx, errors)
    for field in ("labels", "is_blocking", "blocked_by", "acceptance_criteria"):
        _require_list_field(story, field, str, pfx, errors)


def _sprint_json_check_item_type(
    obj: dict[str, Any], pfx: str, expected: str, errors: list[str]
) -> None:
    if "item_type" not in obj:
        errors.append(f"{pfx}: missing required field 'item_type'")
    elif obj["item_type"] != expected:
        errors.append(f"{pfx}.item_type: must be '{expected}', got '{obj['item_type']}'")


def _sprint_json_check_story_values(
    story: dict[str, Any], pfx: str, schema: dict[str, Any], errors: list[str]
) -> None:
    valid_types = set(schema.get("valid_json_story_types", []))
    st = story.get("type")
    if isinstance(st, str) and st not in valid_types:
        errors.append(f"{pfx}.type: '{st}' not in {valid_types}")
    _enum_check(story.get("status", ""), schema.get("valid_story_statuses", []), pfx, "status", errors)
    _enum_check(story.get("priority", ""), schema.get("valid_priorities", []), pfx, "priority", errors)
    id_prefixes = schema.get("json_story_id_prefixes", {})
    sid = story.get("id", "")
    id_prefix = id_prefixes.get(st)
    if id_prefix and isinstance(sid, str):
        pattern = SPECS_ID_REGEX_TEMPLATE.format(prefix=id_prefix)
        if not re.match(pattern, sid):
            errors.append(f"{pfx}.id: '{sid}' does not match pattern for '{st}'")
    for field in ("start_date", "target_date"):
        val = story.get(field)
        if isinstance(val, str) and val and not re.match(_DATE_PATTERN, val):
            errors.append(f"{pfx}.{field}: must be YYYY-MM-DD, got '{val}'")


def _sprint_json_check_task(
    task: dict[str, Any], pfx: str, schema: dict[str, Any],
    errors: list[str], task_ids: set[str],
) -> None:
    _sprint_json_check_task_fields(task, pfx, errors)
    _sprint_json_check_item_type(task, pfx, "task", errors)
    if "type" in task and task["type"] != "task":
        errors.append(f"{pfx}.type: must be 'task', got '{task['type']}'")
    _enum_check(task.get("status", ""), schema.get("valid_json_task_statuses", []), pfx, "status", errors)
    _enum_check(task.get("priority", ""), schema.get("valid_priorities", []), pfx, "priority", errors)
    _enum_check(task.get("complexity", ""), schema.get("valid_complexities", []), pfx, "complexity", errors)
    tid = task.get("id", "")
    if isinstance(tid, str) and not re.match(r"^T-\d+$", tid):
        errors.append(f"{pfx}.id: '{tid}' does not match pattern T-NNN")
    for field in ("start_date", "target_date"):
        val = task.get(field)
        if isinstance(val, str) and val and not re.match(_DATE_PATTERN, val):
            errors.append(f"{pfx}.{field}: must be YYYY-MM-DD, got '{val}'")
    _sprint_json_check_id_refs(task, "is_blocking", pfx, errors, task_ids)
    _sprint_json_check_id_refs(task, "blocked_by", pfx, errors, task_ids)


def _sprint_json_check_task_fields(
    task: dict[str, Any], pfx: str, errors: list[str]
) -> None:
    for field, typ in (
        ("id", str), ("type", str), ("title", str), ("description", str),
        ("status", str), ("priority", str), ("complexity", str),
        ("milestone", str), ("start_date", str), ("target_date", str),
    ):
        _require_field(task, field, typ, pfx, errors)
    for field in ("labels", "is_blocking", "blocked_by", "acceptance_criteria"):
        _require_list_field(task, field, str, pfx, errors)


def _sprint_json_check_id_refs(
    obj: dict[str, Any], field: str, pfx: str, errors: list[str], valid_ids: set[str]
) -> None:
    val = obj.get(field)
    if not isinstance(val, list):
        return
    for ref in val:
        if not isinstance(ref, str):
            errors.append(f"{pfx}.{field}: all entries must be strings")
            break
        if ref not in valid_ids:
            errors.append(f"{pfx}.{field}: '{ref}' references unknown ID")


# ──────────────────────────────────────────────────────────────────
# Sprint MD → JSON converter
# ──────────────────────────────────────────────────────────────────


_SPRINT_META_MAP = {
    "**Sprint #:**": ("sprint", True),
    "**Goal:**": ("description", False),
    "**Milestone:**": ("milestone", False),
    "**Due Date:**": ("due_date", False),
}


def _sprint_md_to_json(content: str) -> dict[str, Any]:
    metadata = _sprint_md_parse_metadata(content)
    stories = _sprint_md_parse_stories(content, metadata["milestone"])
    return {**metadata, "stories": stories}


def _sprint_md_parse_metadata(content: str) -> dict[str, Any]:
    result: dict[str, Any] = {"sprint": 0, "milestone": "", "description": "", "due_date": ""}
    for line in content.split("\n"):
        for prefix, (key, is_int) in _SPRINT_META_MAP.items():
            if line.startswith(prefix):
                value = line.split(prefix, 1)[1].strip()
                result[key] = int(value) if is_int and value.lstrip("-").isdigit() else value
                break
    return result


def _sprint_md_parse_stories(content: str, milestone: str) -> list[dict[str, Any]]:
    pattern = r"#### ([A-Z]{2})-(\d+):\s*(.+?)(?:\n|$)"
    matches = list(re.finditer(pattern, content))
    out: list[dict[str, Any]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block = content[start:end]
        out.append(_sprint_md_build_story(m.group(1), m.group(2), m.group(3).strip(), block, milestone))
    return out


_SPRINT_TYPE_MAP = {"US": "User Story", "TS": "Technical Story", "BG": "Bug", "SK": "Spike"}


def _sprint_md_build_story(
    prefix: str, num: str, title: str, block: str, milestone: str
) -> dict[str, Any]:
    story_id = f"{prefix}-{num}"
    tasks = _sprint_md_parse_tasks(block, milestone)
    if _SPRINT_TYPE_MAP.get(prefix) == "Spike" and not tasks:
        tasks = _sprint_md_spike_as_tasks(block, story_id, milestone)
    _sprint_md_compute_blocking(tasks)
    return {
        "id": story_id,
        "type": _SPRINT_TYPE_MAP.get(prefix, "User Story"),
        "title": title,
        "description": _sprint_md_parse_description(block),
        "acceptance_criteria": _sprint_md_parse_ac_before_tasks(block),
        "item_type": "story",
        "milestone": milestone,
        "tasks": tasks,
        **_sprint_md_parse_story_fields(block),
    }


def _sprint_md_parse_description(block: str) -> str:
    match = re.search(r">\s*(.+?)(?:\n(?!>)|$)", block, re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\n>\s*", " ", match.group(0)).strip().lstrip("> ").strip()


def _sprint_md_parse_ac_before_tasks(block: str) -> list[str]:
    idx = block.find("**Tasks:**")
    ac_block = block[:idx] if idx != -1 else block
    return re.findall(r"- \[[ x]\] (.+)", ac_block)


def _sprint_md_parse_story_fields(block: str) -> dict[str, Any]:
    return {
        "status": _sprint_parse_field(block, "Status") or "Ready",
        "priority": _sprint_parse_field(block, "Priority"),
        "labels": _sprint_parse_csv(_sprint_parse_field(block, "Labels")),
        "points": _sprint_safe_int(_sprint_parse_field(block, "Points")),
        "tdd": _sprint_parse_field(block, "TDD").lower() == "true",
        "is_blocking": _sprint_parse_csv(_sprint_parse_field(block, "Is Blocking")),
        "blocked_by": _sprint_parse_csv(_sprint_parse_field(block, "Blocked By")),
        "start_date": _sprint_parse_field(block, "Start Date"),
        "target_date": _sprint_parse_field(block, "Target Date"),
    }


def _sprint_parse_csv(raw: str) -> list[str]:
    raw = raw.strip()
    if raw in ("-", "None", "none", ""):
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def _sprint_safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _sprint_md_parse_tasks(block: str, milestone: str) -> list[dict[str, Any]]:
    parts = re.split(r"- \*\*T-(\d+):\*\*", block)
    return [
        _sprint_md_build_task(f"T-{parts[i]}", parts[i + 1], milestone)
        for i in range(1, len(parts), 2)
    ]


def _sprint_md_build_task(task_id: str, body: str, milestone: str) -> dict[str, Any]:
    title_match = re.match(r"\s*(.+?)(?:\n|$)", body)
    blocked_by_raw = _sprint_parse_field(body, "Blocked by") or _sprint_parse_field(body, "Depends on")
    return {
        "id": task_id,
        "type": "task",
        "title": title_match.group(1).strip() if title_match else "",
        "is_blocking": [],
        "blocked_by": _sprint_parse_csv(blocked_by_raw),
        "item_type": "task",
        "milestone": milestone,
        "labels": _sprint_parse_csv(_sprint_parse_field(body, "Labels")),
        "description": _sprint_parse_field(body, "Description"),
        "status": _sprint_parse_field(body, "Status") or "Backlog",
        "priority": _sprint_parse_field(body, "Priority"),
        "complexity": _sprint_parse_field(body, "Complexity"),
        "acceptance_criteria": re.findall(r"- \[[ x]\] (.+)", body),
        "start_date": _sprint_parse_field(body, "Start date"),
        "target_date": _sprint_parse_field(body, "Target date"),
    }


def _sprint_md_spike_as_tasks(
    block: str, spike_id: str, milestone: str
) -> list[dict[str, Any]]:
    deliverables = re.findall(r"- \[[ x]\] (.+)", block)
    num = spike_id.split("-")[1]
    return [
        {
            "id": f"T-{num}{idx:02d}",
            "type": "task",
            "labels": ["analysis", "documentation"],
            "title": d,
            "description": "",
            "status": "Backlog",
            "priority": "P1",
            "complexity": "M",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": [d],
            "item_type": "task",
            "milestone": milestone,
            "start_date": "",
            "target_date": "",
        }
        for idx, d in enumerate(deliverables, start=1)
    ]


def _sprint_md_compute_blocking(tasks: list[dict[str, Any]]) -> None:
    task_ids = {t["id"] for t in tasks}
    for task in tasks:
        for dep in task["blocked_by"]:
            if dep in task_ids:
                for other in tasks:
                    if other["id"] == dep and task["id"] not in other["is_blocking"]:
                        other["is_blocking"].append(task["id"])


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

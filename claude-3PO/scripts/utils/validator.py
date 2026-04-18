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
    """Validates specs markdown and converts backlog markdown → JSON.

    Caches one TemplateSchema per doc type for the validator's lifetime.
    Schemas are derived from on-disk template markdown, so re-deriving
    them on every validate() call would be wasteful — caching keeps
    repeated validations cheap during a session.

    Example:
        >>> SpecsValidator(config)  # doctest: +SKIP
    """

    def __init__(self, config):
        """Bind the validator to a runtime config (for ``templates_dir``).

        Args:
            config: Object exposing ``templates_dir`` (a ``Path``).

        Example:
            >>> SpecsValidator(config)  # doctest: +SKIP
        """
        self.config = config
        self._schema_cache: dict[str, TemplateSchema] = {}

    def _schema(self, doc_type: str) -> TemplateSchema:
        """Return a cached or freshly-built TemplateSchema for ``doc_type``.

        Unknown ``doc_type`` returns an empty schema so the caller's
        validators turn into no-ops (fail-open by design — see
        :meth:`TemplateSchema.from_markdown`).

        Args:
            doc_type (str): One of architecture, constitution,
                product_vision, backlog. Anything else yields an empty
                schema.

        Returns:
            TemplateSchema: Cached or newly-loaded schema.

        Example:
            >>> SpecsValidator(config)._schema("architecture")  # doctest: +SKIP
        """
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
        """Run all architecture-doc checks and return collected error strings.

        Args:
            content (str): Architecture markdown body.

        Returns:
            list[str]: Human-readable error messages; empty if valid.

        Example:
            >>> SpecsValidator(_StubCfg()).validate_architecture("")  # doctest: +SKIP
        """
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
        """Run all constitution-doc checks (heading tree + DoD + tooling).

        The constitution validator goes deeper than architecture/vision —
        besides the structural checks, it requires a minimum number of
        numbered governing principles, three Definition-of-Done checklists
        (Task / Story / Sprint), and a tooling table.

        Args:
            content (str): Constitution markdown body.

        Returns:
            list[str]: Human-readable error messages; empty if valid.

        Example:
            >>> SpecsValidator(config).validate_constitution("")  # doctest: +SKIP
        """
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
        """Require at least ``minimum`` numbered bold principles in the section.

        Args:
            content (str): Constitution markdown body.
            minimum (int): Minimum number of principles required.

        Returns:
            list[str]: One error per missing-or-too-few condition; empty if OK.

        Example:
            >>> SpecsValidator._check_governing_principles("", minimum=4)
            ['governing_principles: no numbered principles found']
        """
        count = SpecsValidator._count_numbered_bold_principles(content)
        if count == 0:
            return ["governing_principles: no numbered principles found"]
        if count < minimum:
            return [f"governing_principles: found {count} principles, minimum is {minimum}"]
        return []

    @staticmethod
    def _count_numbered_bold_principles(content: str) -> int:
        """Count ``N. **...`` lines under the Governing Principles section.

        Args:
            content (str): Constitution markdown body.

        Returns:
            int: Number of numbered+bold lines in the section, or 0 if
            the section is missing.

        Example:
            >>> SpecsValidator._count_numbered_bold_principles("# Governing Principles\\n1. **One**\\n")
            1
        """
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
        """Require non-empty ``- [ ]`` checklists under Task/Story/Sprint Done sections.

        Args:
            content (str): Constitution markdown body.

        Returns:
            list[str]: One error per DoD section missing checklist items.

        Example:
            >>> SpecsValidator._check_dod_checklists("")
            ['definition_of_done.Task Done: no checklist items found', 'definition_of_done.Story Done: no checklist items found', 'definition_of_done.Sprint Done: no checklist items found']
        """
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
        """Require a markdown table whose first column header is ``Tool``.

        Args:
            content (str): Constitution markdown body.

        Returns:
            list[str]: One error if no ``| Tool |`` header is found.

        Example:
            >>> SpecsValidator._check_tooling_table("| Tool | Use |")
            []
        """
        if re.search(r"\|\s*Tool\s*\|", content):
            return []
        return ["tooling: tooling table not found (expected '| Tool |' header)"]

    def validate_product_vision(self, content: str) -> list[str]:
        """Run all product-vision checks (metadata, sections, subsections, tables).

        Args:
            content (str): Product-vision markdown body.

        Returns:
            list[str]: Human-readable error messages; empty if valid.

        Example:
            >>> SpecsValidator(config).validate_product_vision("")  # doctest: +SKIP
        """
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
        """Validate a backlog markdown doc (sections + per-story checks).

        Returns early with a single ``no story sections found`` error if
        the doc has no story headings — there's no point per-story
        validating an empty backlog, and surfacing the structural
        problem first is more actionable.

        Args:
            content (str): Backlog markdown body.

        Returns:
            list[str]: Human-readable error messages; empty if valid.

        Example:
            >>> SpecsValidator(config).validate_backlog_md("")  # doctest: +SKIP
        """
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
        """Flag any H2 section in the backlog that isn't in the allowed set.

        Example:
            >>> SpecsValidator._check_backlog_sections("## Foo\\n", ["Stories"])
            ["structure: unknown section '## Foo'"]
        """
        allowed = set(valid)
        return [
            f"structure: unknown section '## {section}'"
            for section in SpecsValidator._headings_at_level(content, 2)
            if section not in allowed
        ]

    def _validate_backlog_item(
        self, item: dict[str, Any], schema: TemplateSchema
    ) -> list[str]:
        """Validate one parsed story item (id, fields, blockquote shape).

        Args:
            item (dict): Story dict produced by :meth:`_parse_story_items`.
            schema (TemplateSchema): Backlog schema with allowed types/priorities.

        Returns:
            list[str]: Per-item errors; empty if the item is valid.

        Example:
            >>> SpecsValidator(config)._validate_backlog_item({}, schema)  # doctest: +SKIP
        """
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
        """Verify a story id has a known type prefix and a valid number suffix.

        Args:
            sid (str): Full story id (e.g. ``"US-001"``).
            prefix (str): Type prefix from the id (``"US"``).
            pfx (str): Error-message prefix for context (e.g. ``"stories.US-001"``).
            valid_types (list[str]): Allowed prefixes from the schema.

        Returns:
            list[str]: One error if the prefix or pattern is invalid.

        Example:
            >>> SpecsValidator._validate_item_id("US-001", "US", "stories.US-001", ["US"])
            []
        """
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
        """Check title/description/priority/AC presence and priority enum.

        Args:
            item (dict): Story dict.
            pfx (str): Error-message prefix.
            valid_priorities (list[str]): Allowed priority labels.

        Returns:
            list[str]: One error per missing or invalid field.

        Example:
            >>> SpecsValidator._validate_item_fields({"title": "", "description": "", "priority": "", "acceptance_criteria": []}, "stories.X", ["P0"])  # doctest: +ELLIPSIS
            ['stories.X.title: is empty', ...]
        """
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
        """Verify the story's blockquote follows the canonical pattern for its type.

        Each story type has a fixed blockquote grammar (US: "As a … I want
        … so that"; BG: "What's broken / Expected / Actual"; etc). When the
        regex misses, the error message names the expected pattern verbatim
        so the author knows exactly what shape to use.

        Args:
            item (dict): Story dict (uses ``blockquotes`` field).
            prefix (str): Type prefix (US/TS/SK/BG).
            pfx (str): Error-message prefix.

        Returns:
            list[str]: One error if the blockquote shape is wrong; empty
            if the type isn't pattern-checked or the pattern matches.

        Example:
            >>> SpecsValidator._validate_item_blockquote({"blockquotes": []}, "ZZ", "stories.X")
            []
        """
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
        """Validate a parsed backlog JSON document.

        Args:
            data (dict): Already-parsed JSON object (typically the output
                of :meth:`convert_backlog_md_to_json`).

        Returns:
            list[str]: Human-readable error messages; empty if valid.

        Example:
            >>> SpecsValidator(config).validate_backlog_json({})  # doctest: +SKIP
        """
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
        """Validate one story object from the JSON form.

        Args:
            story (dict): One story object.
            prefix (str): Error-message prefix (e.g. ``"stories[0]"``).
            schema (TemplateSchema): Backlog schema.

        Returns:
            list[str]: Per-story errors; empty if valid.

        Example:
            >>> SpecsValidator(config)._validate_backlog_story_json({}, "stories[0]", schema)  # doctest: +SKIP
        """
        errors = _check_story_json_fields(story, prefix)
        errors += _check_story_item_type(story, prefix)
        errors += self._check_story_type_and_id(story, prefix, schema)
        errors += self._check_story_enum_values(story, prefix, schema)
        return errors

    def _check_story_type_and_id(
        self, story: dict[str, Any], prefix: str, schema: TemplateSchema
    ) -> list[str]:
        """Verify the JSON ``type`` is recognised and the ``id`` matches its pattern.

        Args:
            story (dict): One story object.
            prefix (str): Error-message prefix.
            schema (TemplateSchema): Backlog schema (provides ``story_type_names``).

        Returns:
            list[str]: One error per invalid type or mismatched id pattern.

        Example:
            >>> SpecsValidator(config)._check_story_type_and_id({}, "stories[0]", schema)  # doctest: +SKIP
        """
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
        """Verify status, priority, and date fields against allowed values/format.

        Args:
            story (dict): One story object.
            prefix (str): Error-message prefix.
            schema (TemplateSchema): Backlog schema.

        Returns:
            list[str]: Per-field errors; empty if all checks pass.

        Example:
            >>> SpecsValidator._check_story_enum_values({}, "stories[0]", schema)  # doctest: +SKIP
        """
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
        """Convert backlog markdown into the canonical JSON object form.

        The JSON shape (``project``, ``goal``, ``dates``, ``totalPoints``,
        ``stories``) matches ``backlog-sample.json`` so downstream tools
        can consume the markdown and JSON interchangeably.

        Args:
            content (str): Backlog markdown body.

        Returns:
            dict: JSON-serialisable backlog object with one entry per
            parsed story.

        Example:
            >>> SpecsValidator(config).convert_backlog_md_to_json("")  # doctest: +SKIP
        """
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
        """Convert one parsed story dict into its canonical JSON shape.

        ``status`` is hard-coded to ``"Backlog"`` for newly-converted
        stories — the markdown form doesn't carry status, and the JSON
        sample treats Backlog as the implicit initial state.

        Args:
            item (dict): Story dict from :meth:`_parse_story_items`.
            type_names (dict[str, str]): Prefix → long-name map (e.g.
                ``{"US": "User Story"}``).

        Returns:
            dict: One JSON story object.

        Example:
            >>> SpecsValidator._story_to_json({"id": "US-001", "title": "T", "description": "D", "priority": "P0", "is_blocking": "", "blocked_by": "", "acceptance_criteria": [], "milestone": ""}, {"US": "User Story"})["type"]
            'User Story'
        """
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
        """Parse a comma-separated list field, treating placeholder text as empty.

        Recognised placeholder strings (``""``, ``"none"``, ``"-"``,
        the templated ``"none / sk-nnn"`` etc.) collapse to ``[]`` so
        the JSON form doesn't ship template stubs as real values.

        Args:
            raw (str): Raw value from the markdown field.

        Returns:
            list[str]: Trimmed entries, with placeholders dropped.

        Example:
            >>> SpecsValidator._parse_list_field("US-001, US-002")
            ['US-001', 'US-002']
            >>> SpecsValidator._parse_list_field("none")
            []
        """
        raw = raw.strip().strip("`").strip("[").strip("]")
        placeholder = {"", "none", "-", "none / sk-nnn", "none / ts-nnn, us-nnn"}
        if raw.lower() in placeholder:
            return []
        return [v.strip() for v in raw.split(",") if v.strip() and v.strip().lower() != "none"]

    @staticmethod
    def _strip_ac_marker(line: str) -> str:
        """Strip the ``- [ ]`` / ``- [x]`` checklist prefix and surrounding backticks.

        Example:
            >>> SpecsValidator._strip_ac_marker("- [ ] Login works")
            'Login works'
        """
        return re.sub(r"^- \[[ x]\] ", "", line).strip("`")

    # ── Shared helpers ────────────────────────────────────────────

    @staticmethod
    def _is_placeholder(value: str) -> bool:
        """Return True if ``value`` is empty or starts with a known template prefix.

        Example:
            >>> SpecsValidator._is_placeholder("")
            True
        """
        return not value or any(value.startswith(p) for p in SPECS_PLACEHOLDER_PREFIXES)

    def _check_bold_metadata(
        self,
        content: str,
        required_fields: list[str],
        *,
        status_field: str | None = None,
        valid_statuses: list[str] | None = None,
    ) -> list[str]:
        """Report missing, placeholder, or invalid-status metadata fields.

        When ``status_field`` is given, also checks that the field's value
        is in ``valid_statuses`` — but skips the check if the value
        contains ``/`` (treated as the template's "Draft / Approved /
        Done" enum line still in place rather than a real status pick).

        Args:
            content (str): Markdown body.
            required_fields (list[str]): Field labels that must appear.
            status_field (str | None): Optional field to enum-check.
            valid_statuses (list[str] | None): Allowed status values.

        Returns:
            list[str]: One error per missing/placeholder/invalid field.

        Example:
            >>> SpecsValidator(config)._check_bold_metadata("", ["Status"])  # doctest: +SKIP
        """
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
        """Return all heading names at ``level`` in document order.

        Example:
            >>> SpecsValidator._headings_at_level("## A\\n## B\\n", 2)
            ['A', 'B']
        """
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
        """Check all required H<level> sections are present; optionally flag unknowns.

        ``flag_unknown=False`` is used by the constitution validator
        because constitution H1s are open-ended (the schema only requires
        a known subset). ``skip_titles`` lets the constitution exclude
        its own document-title H1 from the unknown check.

        Args:
            content (str): Markdown body.
            required (list[str]): Section names that must appear.
            level (int): Heading depth to check.
            allowed_extras (list[str] | None): Extra section names that
                may appear without being flagged unknown.
            flag_unknown (bool): If False, skip the unknown-section pass.
            skip_titles (list[str] | None): Names exempt from both checks.

        Returns:
            list[str]: One error per missing or unexpected section.

        Example:
            >>> SpecsValidator(config)._check_required_sections("## Goals\\n", ["Goals"])  # doctest: +SKIP
        """
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
        self, content: str, required: dict[str, list[str]],
        *, parent_level: int = 2, child_level: int = 3,
    ) -> list[str]:
        """Check each parent section contains its required child-level subsections.

        Args:
            content (str): Markdown body.
            required (dict): Parent name → required child names.
            parent_level (int): Heading depth of parents.
            child_level (int): Heading depth of children.

        Returns:
            list[str]: One error per missing subsection.

        Example:
            >>> SpecsValidator(config)._check_required_subsections("", {})  # doctest: +SKIP
        """
        found = self._collect_subsections(content, parent_level, child_level)
        errors: list[str] = []
        for parent, subs in required.items():
            errors.extend(
                self._missing_subsection_errors(parent, subs, found.get(parent, set()), child_level)
            )
        return errors

    @staticmethod
    def _missing_subsection_errors(
        parent: str, required_subs: list[str], present: set[str], child_level: int
    ) -> list[str]:
        """Build error strings for subsections required but not present.

        Example:
            >>> SpecsValidator._missing_subsection_errors("Foo", ["Bar"], set(), 3)
            ["structure.Foo: missing subsection '### Bar'"]
        """
        marker = "#" * child_level
        return [
            f"structure.{parent}: missing subsection '{marker} {sub}'"
            for sub in required_subs
            if sub not in present
        ]

    @staticmethod
    def _collect_subsections(
        content: str, parent_level: int, child_level: int
    ) -> dict[str, set[str]]:
        """Map each parent-level section to the set of its child-level headings.

        Args:
            content (str): Markdown body.
            parent_level (int): Heading depth of parents.
            child_level (int): Heading depth of children.

        Returns:
            dict[str, set[str]]: ``{parent_name: {child_name, …}}``.

        Example:
            >>> SpecsValidator._collect_subsections("## A\\n### B\\n", 2, 3)
            {'A': {'B'}}
        """
        out: dict[str, set[str]] = {}
        for parent, body in extract_md_sections(content, parent_level):
            children = {name for name, _ in extract_md_sections(body, child_level)}
            out[parent] = children
        return out

    def _check_required_tables(
        self, content: str, table_specs: list[dict[str, str]]
    ) -> list[str]:
        """Each spec declares a section label + a required column header that must appear.

        Lookup is by string match on a ``| Header |`` cell anywhere in
        the document — cheap, deliberately loose (we don't bind the
        table to its declared section, which avoids false negatives when
        authors move tables around).

        Args:
            content (str): Markdown body.
            table_specs (list[dict]): One ``{section, required_header}``
                entry per expected table.

        Returns:
            list[str]: One error per missing required header.

        Example:
            >>> SpecsValidator(config)._check_required_tables("", [])  # doctest: +SKIP
        """
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
        """Parse ``### ID: Title`` items under the ``## Stories`` section.

        Args:
            content (str): Backlog markdown body.

        Returns:
            list[dict]: One story dict per ``### ID: Title`` heading;
            empty if the Stories section is missing.

        Example:
            >>> SpecsValidator._parse_story_items("")
            []
        """
        lines = content.split("\n")
        start = SpecsValidator._find_stories_section(lines)
        if start < 0:
            return []
        items: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for i in range(start + 1, len(lines)):
            current = SpecsValidator._consume_story_line(lines[i], i, current, items)
        if current:
            items.append(current)
        return items

    @staticmethod
    def _consume_story_line(
        line: str, line_idx: int, current: dict | None, items: list[dict]
    ) -> dict | None:
        """Process one line; return the active item (new, current, or None).

        Encountering a new ``### ID: Title`` line flushes the prior item
        into ``items`` and starts a new one. All other lines feed into
        the current item via :meth:`_parse_item_line`.

        Args:
            line (str): Raw markdown line.
            line_idx (int): 0-based line index (passed to ``_new_item``
                as a 1-based ``line_num`` for diagnostics).
            current (dict | None): Item currently being built.
            items (list[dict]): Accumulator of completed items.

        Returns:
            dict | None: The (possibly new) item to keep building.

        Example:
            >>> SpecsValidator._consume_story_line("text", 0, None, [])  # doctest: +SKIP
        """
        match = re.match(r"^### ([\w-]+):\s*(.*)$", line)
        if match:
            if current:
                items.append(current)
            return SpecsValidator._new_item(
                match.group(1), match.group(2).strip().strip("`"), line_idx + 1
            )
        if current:
            SpecsValidator._parse_item_line(current, line.strip())
        return current

    @staticmethod
    def _find_stories_section(lines: list[str]) -> int:
        """Return the line index of ``## Stories``, or -1 if not present.

        Example:
            >>> SpecsValidator._find_stories_section(["## Stories"])
            0
        """
        target = f"## {SPECS_STORIES_HEADING}"
        for i, line in enumerate(lines):
            if line.strip() == target:
                return i
        return -1

    @staticmethod
    def _new_item(sid: str, title: str, line_num: int) -> dict[str, Any]:
        """Construct an empty story dict via the StoryItem model.

        Example:
            >>> SpecsValidator._new_item("US-001", "Login", 1)["id"]
            'US-001'
        """
        from models.story import StoryItem

        return StoryItem.empty(sid, title, line_num)

    @staticmethod
    def _parse_item_line(item: dict[str, Any], stripped: str) -> None:
        """Route one stripped line to blockquote / field / AC bucket of ``item``.

        Field markers (``**Priority:**`` etc.) are matched in order; only
        the first matching marker wins, and only fields the item dict
        already knows about are populated (defensive against template
        drift adding new markers).

        Args:
            item (dict): Story dict to mutate.
            stripped (str): Already-stripped markdown line.

        Example:
            >>> item = {"blockquotes": [], "acceptance_criteria": []}
            >>> SpecsValidator._parse_item_line(item, "> blockquote")
            >>> item["blockquotes"]
            ['> blockquote']
        """
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
    """Append errors when ``obj[field]`` is missing or has the wrong type.

    Args:
        obj (dict): JSON object to check.
        field (str): Field name to look up.
        expected_type (type): Required Python type.
        prefix (str): Error-message prefix (e.g. ``"root"``, ``"stories[0]"``).
        errors (list[str]): Accumulator for error strings (mutated in place).

    Example:
        >>> errors = []
        >>> _require_field({}, "id", str, "root", errors)
        >>> errors
        ["root: missing required field 'id'"]
    """
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
    """Append errors when ``obj[field]`` isn't a list of ``item_type`` values.

    Args:
        obj (dict): JSON object to check.
        field (str): Field name expected to be a list.
        item_type (type): Required type for every list element.
        prefix (str): Error-message prefix.
        errors (list[str]): Accumulator (mutated in place).

    Example:
        >>> errors = []
        >>> _require_list_field({"tags": "x"}, "tags", str, "root", errors)
        >>> errors
        ['root.tags: expected array']
    """
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], list):
        errors.append(f"{prefix}.{field}: expected array")
    elif not all(isinstance(v, item_type) for v in obj[field]):
        errors.append(f"{prefix}.{field}: all entries must be {item_type.__name__}")


def _check_json_root(data: dict[str, Any]) -> list[str]:
    """Validate the top-level fields of a backlog JSON object.

    Args:
        data (dict): Parsed JSON document.

    Returns:
        list[str]: One error per missing or wrongly-typed root field.

    Example:
        >>> _check_json_root({})  # doctest: +ELLIPSIS
        ["root: missing required field 'project'", ...]
    """
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
    """Validate the ``dates`` object's ``start`` and ``end`` fields.

    Args:
        data (dict): Parsed JSON document.

    Returns:
        list[str]: One error per missing/typed/format violation.

    Example:
        >>> _check_json_dates({})
        ["root: missing required field 'dates'"]
    """
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
    """Validate the scalar string and list fields of one JSON story.

    Args:
        story (dict): One story object.
        prefix (str): Error-message prefix.

    Returns:
        list[str]: Per-field errors.

    Example:
        >>> _check_story_json_fields({}, "stories[0]")  # doctest: +ELLIPSIS
        ["stories[0]: missing required field 'id'", ...]
    """
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
    """Require ``item_type == "story"`` on every backlog JSON story.

    Args:
        story (dict): One story object.
        prefix (str): Error-message prefix.

    Returns:
        list[str]: One error if the field is missing or has another value.

    Example:
        >>> _check_story_item_type({"item_type": "story"}, "stories[0]")
        []
    """
    if "item_type" not in story:
        return [f"{prefix}: missing required field 'item_type'"]
    if story["item_type"] != "story":
        return [f"{prefix}.item_type: must be 'story', got '{story['item_type']}'"]
    return []


# Backwards-compatible module-level entry points (used by utils/specs_writer.py).

def _default_validator() -> SpecsValidator:
    """Build a SpecsValidator bound to a default Config — used by the back-compat helpers.

    Example:
        >>> _default_validator()  # doctest: +SKIP
    """
    from config import Config
    return SpecsValidator(Config())


def validate_architecture(content: str) -> list[str]:
    """Module-level back-compat wrapper around :meth:`SpecsValidator.validate_architecture`.

    Args:
        content (str): Architecture markdown body.

    Returns:
        list[str]: Validation errors (empty if valid).

    Example:
        >>> validate_architecture("")  # doctest: +SKIP
    """
    return _default_validator().validate_architecture(content)


def validate_backlog_md(content: str) -> list[str]:
    """Module-level back-compat wrapper around :meth:`SpecsValidator.validate_backlog_md`.

    Args:
        content (str): Backlog markdown body.

    Returns:
        list[str]: Validation errors (empty if valid).

    Example:
        >>> validate_backlog_md("")  # doctest: +SKIP
    """
    return _default_validator().validate_backlog_md(content)


def convert_backlog_md_to_json(content: str) -> dict[str, Any]:
    """Module-level back-compat wrapper around :meth:`SpecsValidator.convert_backlog_md_to_json`.

    Args:
        content (str): Backlog markdown body.

    Returns:
        dict: JSON-serialisable backlog object.

    Example:
        >>> convert_backlog_md_to_json("")  # doctest: +SKIP
    """
    return _default_validator().convert_backlog_md_to_json(content)

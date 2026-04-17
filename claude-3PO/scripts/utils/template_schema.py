"""TemplateSchema — derives validation schemas directly from the
canonical markdown templates in ``claude-3PO/templates/``.

The template markdown file the human edits is the **single source of
truth**: editing it is the only change needed to update the contract.
``SpecsValidator`` calls ``TemplateSchema.from_file(...)`` once per doc
type and validates agent reports against the resulting schema.

Each factory classmethod builds a ``TemplateSchema`` for one doc type by
composing small, single-purpose parsers (``_parse_*`` / ``_collect_*``)
so each parsing rule lives in one named place rather than buried in a
600-line validator.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lib.extractors import extract_bold_metadata, extract_md_sections, extract_table


_NUMBERED_H2 = re.compile(r"^\d+\.\s")
_NUMBERED_H3 = re.compile(r"^\d+\.\d+\s")
_BLOCKQUOTE_META = re.compile(r"^>\s*\*\*([^*:]+?):\*\*\s*(.*)$")


@dataclass
class TemplateSchema:
    """Structural schema derived from a spec template markdown file.

    Fields are populated selectively by the per-doc-type builders — most
    schemas use only a subset (e.g. backlog uses ``valid_priorities`` /
    ``valid_item_types`` / ``json_item_statuses`` which the others leave empty).
    Each ``required_*`` collection is what the validator checks for *presence*;
    ``allowed_extra_sections`` lists names that may appear but aren't required.
    """

    metadata_fields: list[str] = field(default_factory=list)
    status_enums: dict[str, list[str]] = field(default_factory=dict)
    required_sections: list[str] = field(default_factory=list)
    required_subsections: dict[str, list[str]] = field(default_factory=dict)
    required_tables: list[dict[str, str]] = field(default_factory=list)
    allowed_extra_sections: list[str] = field(default_factory=list)
    doc_title: str = ""
    required_h3_subsections: dict[str, list[str]] = field(default_factory=dict)
    valid_priorities: list[str] = field(default_factory=list)
    valid_item_types: list[str] = field(default_factory=list)
    story_type_names: dict[str, str] = field(default_factory=dict)
    json_item_statuses: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path, doc_type: str) -> "TemplateSchema":
        """
        Read a template markdown file and derive a TemplateSchema.

        ``path.parent`` is forwarded to the builder so doc types that need
        sibling files (e.g. backlog reads ``backlog-sample.json`` next door)
        can locate them.

        Args:
            path (Path): Absolute path to the template markdown file.
            doc_type (str): One of ``architecture``, ``constitution``,
                ``product_vision``, ``backlog``. Unknown values yield an
                empty schema (see :meth:`from_markdown`).

        Returns:
            TemplateSchema: Schema instance populated by the matching builder.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            OSError: If ``path`` cannot be read.

        Example:
            >>> schema = TemplateSchema.from_file(
            ...     Path("templates/architecture.md"), "architecture"
            ... )
            >>> "1. Overview" in schema.required_sections
            True
        """
        text = path.read_text(encoding="utf-8")
        return cls.from_markdown(text, doc_type, path.parent)

    @classmethod
    def from_markdown(
        cls, text: str, doc_type: str, templates_dir: Path | None = None
    ) -> "TemplateSchema":
        """
        Dispatch to the per-doc-type builder for a markdown template.

        Unknown ``doc_type`` returns an empty schema rather than raising —
        callers stay responsible for choosing a valid type, and an empty
        schema makes every validation a no-op (fail-open, by design, since
        spec validation is advisory metadata, not a security boundary).

        Args:
            text (str): Raw template markdown.
            doc_type (str): One of ``architecture``, ``constitution``,
                ``product_vision``, ``backlog``. Anything else returns an empty schema.
            templates_dir (Path | None): Directory containing sibling template
                files (only used by the backlog builder for ``backlog-sample.json``).

        Returns:
            TemplateSchema: Populated schema, or an empty one for unknown ``doc_type``.

        Example:
            >>> TemplateSchema.from_markdown("", "unknown-type").required_sections
            []
        """
        builders = {
            "architecture": _build_architecture_schema,
            "constitution": _build_constitution_schema,
            "product_vision": _build_product_vision_schema,
            "backlog": _build_backlog_schema,
        }
        builder = builders.get(doc_type)
        if builder is None:
            return cls()
        return builder(text, templates_dir)


# ── Shared parsers (small, composable) ────────────────────────────


def _parse_metadata_block(text: str) -> dict[str, str]:
    """
    Extract field/value pairs from the document header.

    The "header" is everything before the first H2 line. Two formats are
    supported because the templates use both: plain ``**Label:** value`` lines
    and blockquote-wrapped ``> **Label:** value`` lines (the latter typically
    inside a ``> Status / Owner / …`` callout block).

    Args:
        text (str): Full template markdown.

    Returns:
        dict[str, str]: Field name → value, with both bold and blockquote-bold
        forms merged into one mapping.

    Example:
        >>> md = "**Status:** Draft\\n\\n## Overview\\n"
        >>> _parse_metadata_block(md)
        {'Status': 'Draft'}
    """
    head_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            break
        head_lines.append(line)
    head = "\n".join(head_lines)
    meta = extract_bold_metadata(head)
    for line in head_lines:
        match = _BLOCKQUOTE_META.match(line.strip())
        if match:
            meta[match.group(1).strip()] = match.group(2).strip().strip("`")
    return meta


def _parse_status_enums(metadata: dict[str, str]) -> dict[str, list[str]]:
    """
    Treat any metadata value containing ``" / "`` as an enum of allowed values.

    Convention: template authors write ``**Status:** Draft / Approved / Done`` to
    declare both the field name *and* its allowed values in one line. Two or more
    parts required so a stray slash in prose doesn't accidentally create an enum.

    Args:
        metadata (dict[str, str]): Output of :func:`_parse_metadata_block`.

    Returns:
        dict[str, list[str]]: Field name → list of enum values, including only
        fields whose value parsed into 2+ non-empty parts.

    Example:
        >>> _parse_status_enums({"Status": "Draft / Approved / Done"})
        {'Status': ['Draft', 'Approved', 'Done']}
    """
    enums: dict[str, list[str]] = {}
    for label, value in metadata.items():
        if " / " in value:
            parts = [p.strip() for p in value.split(" / ") if p.strip()]
            if len(parts) >= 2:
                enums[label] = parts
    return enums


def _h3_children(h2_body: str) -> list[str]:
    """
    List the H3 headings directly inside an H2 body.

    Args:
        h2_body (str): Markdown body of an H2 section (everything between
            this H2 and the next H2 — *not* the H2 line itself).

    Returns:
        list[str]: H3 heading names in document order.

    Example:
        >>> _h3_children("### Goals\\nbody\\n### Non-Goals\\nbody")
        ['Goals', 'Non-Goals']
    """
    return [name for name, _ in extract_md_sections(h2_body, 3)]


def _first_table_first_header(body: str) -> str | None:
    """
    Return the top-left header cell of the first table in ``body``.

    Used as a fingerprint for "this section requires a table whose first column
    is named X" — schemas store that header so the validator can later confirm
    a real document still has a table with a matching first column.

    Args:
        body (str): Markdown body to scan.

    Returns:
        str | None: The trimmed top-left header text, or ``None`` if no table
        is found or the first cell is empty.

    Example:
        >>> _first_table_first_header("| ID | Name |\\n|----|------|\\n| 1 | x |")
        'ID'
    """
    table = extract_table(body)
    if not table or not table[0]:
        return None
    first = table[0][0].strip()
    return first or None


def _body_before_h3(h2_body: str) -> str:
    """
    Return the H2 body up to (but not including) the first H3 heading.

    Lets table-collection treat the H2's own intro paragraph separately from
    its H3 subsections — the intro may contain a top-level table that belongs
    to the H2, not to any one H3.

    Args:
        h2_body (str): Markdown body of an H2 section.

    Returns:
        str: Substring up to the first ``### `` line; the full body if no H3 exists.

    Example:
        >>> _body_before_h3("intro line\\n### sub\\nignored")
        'intro line\\n'
    """
    split = re.split(r"^###\s+", h2_body, maxsplit=1, flags=re.MULTILINE)
    return split[0]


# ── Architecture ──────────────────────────────────────────────────


def _build_architecture_schema(
    text: str, _templates_dir: Path | None
) -> TemplateSchema:
    """
    Build the architecture-document schema.

    Architecture templates use the leading number of an H2 to mark required
    sections. ``## 1. Overview`` / ``## 2. Modules`` are required (numbered →
    must appear); free-form ``## Notes`` / ``## References`` headings become
    ``allowed_extra_sections`` so they're permitted but not enforced. The same
    numbering convention applies to H3s.

    Args:
        text (str): Architecture template markdown.
        _templates_dir (Path | None): Unused; present for builder-signature uniformity.

    Returns:
        TemplateSchema: Schema with ``required_sections`` (numbered H2s),
        ``required_subsections`` (numbered H3s under numbered H2s), and
        ``allowed_extra_sections`` (un-numbered H2s).
    """
    metadata = _parse_metadata_block(text)
    all_h2 = [name for name, _ in extract_md_sections(text, 2)]
    required_h2 = [name for name in all_h2 if _NUMBERED_H2.match(name)]
    extras = [name for name in all_h2 if not _NUMBERED_H2.match(name)]
    return TemplateSchema(
        metadata_fields=list(metadata.keys()),
        status_enums=_parse_status_enums(metadata),
        required_sections=required_h2,
        required_subsections=_architecture_subsections(text),
        allowed_extra_sections=extras,
    )


def _architecture_subsections(text: str) -> dict[str, list[str]]:
    """
    Map each numbered H2 to its required (numbered) H3 children.

    Args:
        text (str): Architecture template markdown.

    Returns:
        dict[str, list[str]]: ``{h2_name: [h3_name, ...]}`` — only entries
        with at least one numbered H3 child are included.

    Example:
        >>> md = "## 1. Overview\\n### 1.1 Goals\\n### Notes\\n## 2. Modules\\n"
        >>> _architecture_subsections(md)
        {'1. Overview': ['1.1 Goals']}
    """
    out: dict[str, list[str]] = {}
    for h2_name, h2_body in extract_md_sections(text, 2):
        if not _NUMBERED_H2.match(h2_name):
            continue
        h3s = [name for name in _h3_children(h2_body) if _NUMBERED_H3.match(name)]
        if h3s:
            out[h2_name] = h3s
    return out


# ── Constitution ──────────────────────────────────────────────────


def _build_constitution_schema(
    text: str, _templates_dir: Path | None
) -> TemplateSchema:
    """
    Build the constitution-document schema.

    Constitution templates use three heading levels — H1 sections, H2 subsections,
    H3 sub-subsections. The first H1 is treated as the document title (stored as
    ``doc_title``) and excluded from ``required_sections`` so the schema doesn't
    demand the title repeat itself inside the body.

    Args:
        text (str): Constitution template markdown.
        _templates_dir (Path | None): Unused; present for builder-signature uniformity.

    Returns:
        TemplateSchema: Schema with ``doc_title``, ``required_sections`` (H1s
        excluding title), ``required_subsections`` (H2s under each H1), and
        ``required_h3_subsections`` (H3s under each H2).
    """
    metadata = _parse_metadata_block(text)
    h1s = [name for name, _ in extract_md_sections(text, 1)]
    title = h1s[0] if h1s else ""
    required, h2_by_h1, h3_by_h2 = _constitution_sections(text, title)
    return TemplateSchema(
        metadata_fields=list(metadata.keys()),
        required_sections=required,
        required_subsections=h2_by_h1,
        required_h3_subsections=h3_by_h2,
        doc_title=title,
    )


def _constitution_sections(
    text: str, title: str
) -> tuple[list[str], dict[str, list[str]], dict[str, list[str]]]:
    """
    Walk the constitution heading tree and return three parallel maps.

    Args:
        text (str): Constitution template markdown.
        title (str): Document title (the first H1) — skipped while walking
            so it doesn't appear in the required-sections list.

    Returns:
        tuple[list[str], dict[str, list[str]], dict[str, list[str]]]:
            ``(required_h1s, {h1: [h2s]}, {h2: [h3s]})`` — the first element is
            the list of H1 section names to require; the maps are populated only
            for parents that have children at the next level.
    """
    required: list[str] = []
    h2_map: dict[str, list[str]] = {}
    h3_map: dict[str, list[str]] = {}
    for h1_name, h1_body in extract_md_sections(text, 1):
        if h1_name == title:
            continue
        required.append(h1_name)
        h2s = list(extract_md_sections(h1_body, 2))
        if h2s:
            h2_map[h1_name] = [name for name, _ in h2s]
        for h2_name, h2_body in h2s:
            children = _h3_children(h2_body)
            if children:
                h3_map[h2_name] = children
    return required, h2_map, h3_map


# ── Product Vision ────────────────────────────────────────────────


def _build_product_vision_schema(
    text: str, _templates_dir: Path | None
) -> TemplateSchema:
    """
    Build the product-vision schema.

    Product-vision templates treat *every* H2 as required (no numbering
    convention). Differs from ``architecture`` (numbered-only) — vision
    documents have a fixed canonical structure where every section must be
    present, so the template's H2 set is the schema's required-set verbatim.

    Args:
        text (str): Product-vision template markdown.
        _templates_dir (Path | None): Unused; present for builder-signature uniformity.

    Returns:
        TemplateSchema: Schema with all H2s required, H3 children mapped per H2,
        and any tables fingerprinted via ``required_tables``.
    """
    metadata = _parse_metadata_block(text)
    sections = [name for name, _ in extract_md_sections(text, 2)]
    subsections: dict[str, list[str]] = {}
    for h2_name, h2_body in extract_md_sections(text, 2):
        h3s = _h3_children(h2_body)
        if h3s:
            subsections[h2_name] = h3s
    return TemplateSchema(
        metadata_fields=list(metadata.keys()),
        required_sections=sections,
        required_subsections=subsections,
        required_tables=_collect_required_tables(text),
    )


def _collect_required_tables(text: str) -> list[dict[str, str]]:
    """
    Walk every H2/H3 body and record the first header cell of any table found.

    Each H3 with a table contributes one entry; an H2's pre-H3 intro body is
    also scanned (via :func:`_body_before_h3`) so tables that belong to the H2
    itself aren't missed.

    Args:
        text (str): Product-vision template markdown.

    Returns:
        list[dict[str, str]]: One ``{"section": name, "required_header": col}``
        entry per detected table, in document order.

    Example:
        >>> md = "## Goals\\n| Goal |\\n|------|\\n| ship |\\n"
        >>> _collect_required_tables(md)
        [{'section': 'Goals', 'required_header': 'Goal'}]
    """
    tables: list[dict[str, str]] = []
    for h2_name, h2_body in extract_md_sections(text, 2):
        for h3_name, h3_body in extract_md_sections(h2_body, 3):
            header = _first_table_first_header(h3_body)
            if header:
                tables.append({"section": h3_name, "required_header": header})
        h2_pre = _body_before_h3(h2_body)
        header = _first_table_first_header(h2_pre)
        if header:
            tables.append({"section": h2_name, "required_header": header})
    return tables


# ── Backlog ───────────────────────────────────────────────────────


def _build_backlog_schema(
    text: str, templates_dir: Path | None
) -> TemplateSchema:
    """
    Build the backlog-document schema.

    Backlog has the richest schema — pulled from three places in the template family:

    - ``## Priority Legend`` bullets → ``valid_priorities`` (P0/P1/P2 …)
    - ``## ID Conventions`` table → ``valid_item_types`` + ``story_type_names`` (US/TS/SK/BG …)
    - ``backlog-sample.json`` (sibling file) → ``json_item_statuses``

    Statuses live in the JSON sample rather than the markdown because they
    constrain the *generated* JSON schema, not the markdown the user writes.

    Args:
        text (str): Backlog template markdown.
        templates_dir (Path | None): Directory containing the sibling
            ``backlog-sample.json``. ``None`` disables status extraction.

    Returns:
        TemplateSchema: Populated with all five backlog-specific fields plus
        the standard ``metadata_fields`` and ``required_sections``.
    """
    metadata = _parse_metadata_block(text)
    sections = [name for name, _ in extract_md_sections(text, 2)]
    priorities = _parse_priority_legend(text)
    item_types, type_names = _parse_id_conventions(text)
    statuses = _parse_backlog_sample_statuses(templates_dir)
    return TemplateSchema(
        metadata_fields=list(metadata.keys()),
        required_sections=sections,
        valid_priorities=priorities,
        valid_item_types=item_types,
        story_type_names=type_names,
        json_item_statuses=statuses,
    )


def _parse_priority_legend(text: str) -> list[str]:
    """
    Extract priority codes from ``- **Pn** — ...`` bullets under ``## Priority Legend``.

    Args:
        text (str): Backlog template markdown.

    Returns:
        list[str]: Priority labels in document order (e.g. ``["P0", "P1", "P2"]``);
        empty if the section is missing or contains no bold-prefixed bullets.

    Example:
        >>> md = "## Priority Legend\\n- **P0** — must ship\\n- **P1** — soon\\n"
        >>> _parse_priority_legend(md)
        ['P0', 'P1']
    """
    for h2_name, h2_body in extract_md_sections(text, 2):
        if h2_name.strip() != "Priority Legend":
            continue
        found: list[str] = []
        for line in h2_body.splitlines():
            m = re.match(r"^-\s+\*\*([^*]+?)\*\*", line.strip())
            if m:
                found.append(m.group(1).strip())
        return found
    return []


def _parse_id_conventions(text: str) -> tuple[list[str], dict[str, str]]:
    """
    Pull item-type prefixes and their long names from the ``## ID Conventions`` table.

    Args:
        text (str): Backlog template markdown.

    Returns:
        tuple[list[str], dict[str, str]]: ``(prefixes, {prefix: type_name})``;
        both empty if the section or table is missing.
    """
    for h2_name, h2_body in extract_md_sections(text, 2):
        if h2_name.strip() != "ID Conventions":
            continue
        return _rows_to_type_map(extract_table(h2_body))
    return [], {}


def _rows_to_type_map(table: list[list[str]]) -> tuple[list[str], dict[str, str]]:
    """
    Collapse an ID-Conventions table into a prefix list and a prefix→name map.

    The table's first column holds example IDs like ``US-001``; we keep only the
    prefix before the dash (``US``) since IDs in real backlogs use sequential
    numbers per prefix. Header row is skipped via ``table[1:]``.

    Args:
        table (list[list[str]]): Parsed rows including the header at index 0.
            Rows shorter than 2 columns are ignored.

    Returns:
        tuple[list[str], dict[str, str]]: ``(prefixes, {prefix: type_name})``
        in document order; both empty if no usable rows.

    Example:
        >>> _rows_to_type_map([["ID", "Type"], ["US-001", "User Story"]])
        (['US'], {'US': 'User Story'})
    """
    types: list[str] = []
    names: dict[str, str] = {}
    for row in table[1:]:
        if len(row) < 2:
            continue
        prefix = row[0].split("-")[0].strip()
        type_name = row[1].strip()
        if prefix and type_name:
            types.append(prefix)
            names[prefix] = type_name
    return types, names


def _parse_backlog_sample_statuses(templates_dir: Path | None) -> list[str]:
    """
    Extract every distinct ``status`` value seen in ``backlog-sample.json``.

    Status values aren't enumerated in the markdown template — the sample JSON
    next to it is the source of truth (it doubles as a hand-written reference
    schema). Missing file or missing ``templates_dir`` returns an empty list,
    which deliberately disables status enforcement rather than failing closed.

    Args:
        templates_dir (Path | None): Directory expected to contain
            ``backlog-sample.json``. ``None`` short-circuits to ``[]``.

    Returns:
        list[str]: Distinct ``status`` strings, in first-seen order.

    Raises:
        json.JSONDecodeError: If ``backlog-sample.json`` exists but is malformed
            (deliberately propagated — a corrupt sample file is an authoring bug
            that should fail loudly).
    """
    if templates_dir is None:
        return []
    sample = templates_dir / "backlog-sample.json"
    if not sample.exists():
        return []
    data = json.loads(sample.read_text(encoding="utf-8"))
    seen: list[str] = []
    for story in data.get("stories", []):
        status = story.get("status")
        if isinstance(status, str) and status and status not in seen:
            seen.append(status)
    return seen

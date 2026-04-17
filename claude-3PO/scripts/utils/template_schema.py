"""TemplateSchema — derives validation schemas directly from the
canonical markdown templates in claude-3PO/templates/.

The template file the human edits is the single source of truth.
Each factory classmethod builds a TemplateSchema for one doc type by
composing small, single-purpose parsers.
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
    """Structural schema derived from a spec template markdown file."""

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
        text = path.read_text(encoding="utf-8")
        return cls.from_markdown(text, doc_type, path.parent)

    @classmethod
    def from_markdown(
        cls, text: str, doc_type: str, templates_dir: Path | None = None
    ) -> "TemplateSchema":
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
    """Return {field: value} from bold or blockquote-bold lines before first H2."""
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
    """Any metadata value with ' / ' separators becomes an enum list."""
    enums: dict[str, list[str]] = {}
    for label, value in metadata.items():
        if " / " in value:
            parts = [p.strip() for p in value.split(" / ") if p.strip()]
            if len(parts) >= 2:
                enums[label] = parts
    return enums


def _h3_children(h2_body: str) -> list[str]:
    return [name for name, _ in extract_md_sections(h2_body, 3)]


def _first_table_first_header(body: str) -> str | None:
    table = extract_table(body)
    if not table or not table[0]:
        return None
    first = table[0][0].strip()
    return first or None


def _body_before_h3(h2_body: str) -> str:
    """Return the H2 body up to (but not including) the first H3 heading."""
    split = re.split(r"^###\s+", h2_body, maxsplit=1, flags=re.MULTILINE)
    return split[0]


# ── Architecture ──────────────────────────────────────────────────


def _build_architecture_schema(
    text: str, _templates_dir: Path | None
) -> TemplateSchema:
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
    """H3 children of each numbered H2, restricted to numbered H3s."""
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
    """Walk H2/H3 bodies and record the first header cell of any table found."""
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
    """Extract P0/P1/P2 from `- **Pn** — ...` bullets under `## Priority Legend`."""
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
    """Pull item-type prefixes and their long names from the ID Conventions table."""
    for h2_name, h2_body in extract_md_sections(text, 2):
        if h2_name.strip() != "ID Conventions":
            continue
        return _rows_to_type_map(extract_table(h2_body))
    return [], {}


def _rows_to_type_map(table: list[list[str]]) -> tuple[list[str], dict[str, str]]:
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

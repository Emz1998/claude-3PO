"""Validate product-vision.md against the template structure."""

import re

REQUIRED_METADATA = {
    "**Project:**": "Project",
    "**Version:**": "Version",
    "**Author:**": "Author",
    "**Last Updated:**": "Last Updated",
}

REQUIRED_SECTIONS = {
    "Vision Statement",
    "The Problem",
    "The Solution",
    "Market Landscape",
    "Strategy",
    "Business Model",
    "Risks & Mitigations",
    "Team & Resources",
    "Success Criteria",
    "Appendix",
    "Document History",
}

REQUIRED_SUBSECTIONS = {
    "The Problem": {"Who Has This Problem?", "What's Broken Today?", "Why Now?"},
    "The Solution": {"Product in One Paragraph", "Core Value Propositions", "How It Works (High Level)"},
    "Market Landscape": {"Competitive Positioning", "Defensibility"},
    "Strategy": {"MVP Scope", "What's Explicitly NOT in MVP", "Product Roadmap (High Level)"},
    "Business Model": {"Revenue Model", "Key Metrics", "Unit Economics (If Known)"},
    "Team & Resources": {"Current Runway / Budget"},
    "Success Criteria": {"MVP Launch (Go / No-Go)", "6-Month Vision", "12-Month Vision"},
    "Appendix": {"Glossary", "References"},
}


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    sections = _parse_sections(lines)
    _validate_sections(sections, errors)
    _validate_subsections(lines, errors)
    _validate_tables(content, errors)

    return errors


def _validate_metadata(lines: list[str], errors: list[str]) -> None:
    for key, label in REQUIRED_METADATA.items():
        found = [line for line in lines if key in line]
        if not found:
            errors.append(f"metadata: missing required field '{label}'")
        else:
            value = found[0].split(key)[1].strip().strip("`")
            if not value or value.startswith("[") or value.startswith("<"):
                errors.append(f"metadata.{label}: field is empty or placeholder")


def _parse_sections(lines: list[str]) -> set[str]:
    sections: set[str] = set()
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            sections.add(line[3:].strip())
    return sections


def _validate_sections(sections: set[str], errors: list[str]) -> None:
    for req in REQUIRED_SECTIONS:
        if req not in sections:
            errors.append(f"structure: missing required section '## {req}'")

    allowed = REQUIRED_SECTIONS
    for section in sections:
        if section not in allowed:
            errors.append(f"structure: unknown section '## {section}'")


def _validate_subsections(lines: list[str], errors: list[str]) -> None:
    current_section = ""
    found_subsections: dict[str, set[str]] = {}

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            current_section = line[3:].strip()
            if current_section not in found_subsections:
                found_subsections[current_section] = set()
        elif line.startswith("### ") and current_section:
            found_subsections[current_section].add(line[4:].strip())

    for section, required_subs in REQUIRED_SUBSECTIONS.items():
        found = found_subsections.get(section, set())
        for sub in required_subs:
            if sub not in found:
                errors.append(f"structure.{section}: missing subsection '### {sub}'")


def _validate_tables(content: str, errors: list[str]) -> None:
    required_tables = [
        ("Who Has This Problem?", ["Segment", "Description", "Size"]),
        ("Core Value Propositions", ["#", "Value Proposition", "User Benefit"]),
        ("Competitive Positioning", ["Competitor / Alternative"]),
        ("MVP Scope", ["Feature"]),
        ("Revenue Model", ["Model", "Description"]),
        ("Key Metrics", ["Metric", "Definition", "MVP Target"]),
        ("Risks & Mitigations", ["Risk", "Impact", "Likelihood", "Mitigation"]),
        ("Team & Resources", ["Role", "Who", "Status"]),
        ("Document History", ["Version", "Date", "Author", "Changes"]),
    ]

    for table_context, required_headers in required_tables:
        # Check if at least the first required header appears in a table row
        pattern = rf"\|\s*{re.escape(required_headers[0])}\s*\|"
        if not re.search(pattern, content):
            errors.append(f"table.{table_context}: table not found or missing header '{required_headers[0]}'")

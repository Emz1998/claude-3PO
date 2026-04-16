"""Validate constitution.md against the template structure."""

import re

REQUIRED_METADATA = {
    "**Project:**": "Project",
    "**Version:**": "Version",
    "**Last Updated:**": "Last Updated",
    "**Maintained by:**": "Maintained by",
}

# Top-level sections use # (h1) in the constitution template
REQUIRED_H1_SECTIONS = {
    "Governing Principles",
    "Development Guidelines",
    "Coding Standards",
    "Testing Policy",
    "Definition of Done",
    "Tooling",
}

REQUIRED_H2_SECTIONS = {
    "Development Guidelines": {
        "Workflow",
        "Decision-Making",
        "Dependencies",
        "Version Control",
        "Security",
    },
    "Coding Standards": {
        "Language & Type Safety",
        "Naming Conventions",
        "Formatting",
        "Code Structure",
        "Comments & Documentation",
        "Error Handling",
    },
    "Testing Policy": {
        "Required Tests",
        "Exempt from Tests",
        "Test Standards",
    },
    "Definition of Done": {
        "Task Done",
        "Story Done",
        "Sprint Done",
        "Out of Scope",
    },
}

REQUIRED_H3_SUBSECTIONS = {
    "Version Control": {"Branch Naming", "Commit Messages"},
    "Code Structure": {"Directory Structure"},
}

# Optional sections that are valid but not required
OPTIONAL_H2_SECTIONS = {
    "How to Use This Document",
    "AI-Specific Standards",
}


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    _validate_h1_sections(lines, errors)
    _validate_h2_sections(lines, errors)
    _validate_h3_subsections(lines, errors)
    _validate_governing_principles(lines, errors)
    _validate_dod_checklists(lines, errors)
    _validate_tooling_table(content, errors)

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


def _validate_h1_sections(lines: list[str], errors: list[str]) -> None:
    found_h1: set[str] = set()
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            section = line[2:].strip()
            # Skip the document title (first h1)
            if section == "Project Constitution":
                continue
            found_h1.add(section)

    for req in REQUIRED_H1_SECTIONS:
        if req not in found_h1:
            errors.append(f"structure: missing required section '# {req}'")

    allowed = REQUIRED_H1_SECTIONS | {"Project Constitution", "Appendix — Agent Reference"}
    for section in found_h1:
        if section not in allowed:
            errors.append(f"structure: unknown section '# {section}'")


def _validate_h2_sections(lines: list[str], errors: list[str]) -> None:
    current_h1 = ""
    found_h2: dict[str, set[str]] = {}

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            current_h1 = line[2:].strip()
            if current_h1 not in found_h2:
                found_h2[current_h1] = set()
        elif line.startswith("## ") and not line.startswith("### "):
            section = line[3:].strip()
            if current_h1:
                found_h2[current_h1].add(section)

    for h1, required_h2s in REQUIRED_H2_SECTIONS.items():
        found = found_h2.get(h1, set())
        for sub in required_h2s:
            if sub not in found:
                errors.append(f"structure.{h1}: missing subsection '## {sub}'")


def _validate_h3_subsections(lines: list[str], errors: list[str]) -> None:
    current_h2 = ""
    found_h3: dict[str, set[str]] = {}

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            current_h2 = line[3:].strip()
            if current_h2 not in found_h3:
                found_h3[current_h2] = set()
        elif line.startswith("### ") and current_h2:
            found_h3[current_h2].add(line[4:].strip())

    for h2, required_h3s in REQUIRED_H3_SUBSECTIONS.items():
        found = found_h3.get(h2, set())
        for sub in required_h3s:
            if sub not in found:
                errors.append(f"structure.{h2}: missing subsection '### {sub}'")


def _validate_governing_principles(lines: list[str], errors: list[str]) -> None:
    in_principles = False
    principle_count = 0

    for line in lines:
        if line.startswith("# Governing Principles"):
            in_principles = True
            continue
        if in_principles and line.startswith("# ") and not line.startswith("## "):
            break
        if in_principles and re.match(r"^\d+\.\s+\*\*", line):
            principle_count += 1

    if principle_count == 0:
        errors.append("governing_principles: no numbered principles found")
    elif principle_count < 4:
        errors.append(f"governing_principles: found {principle_count} principles, minimum is 4")


def _validate_dod_checklists(lines: list[str], errors: list[str]) -> None:
    dod_sections = {"Task Done", "Story Done", "Sprint Done"}
    current_dod = ""
    checklist_counts: dict[str, int] = {}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            if section in dod_sections:
                current_dod = section
                checklist_counts[current_dod] = 0
            else:
                current_dod = ""
        elif current_dod and (stripped.startswith("- [ ]") or stripped.startswith("- [x]")):
            checklist_counts[current_dod] = checklist_counts.get(current_dod, 0) + 1

    for section in dod_sections:
        count = checklist_counts.get(section, 0)
        if count == 0:
            errors.append(f"definition_of_done.{section}: no checklist items found")


def _validate_tooling_table(content: str, errors: list[str]) -> None:
    if not re.search(r"\|\s*Tool\s*\|", content):
        errors.append("tooling: tooling table not found (expected '| Tool |' header)")

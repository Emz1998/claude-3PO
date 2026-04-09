"""Validate architecture.md against the template structure."""

import re

REQUIRED_METADATA = {
    "**Project Name:**": "Project Name",
    "**Version:**": "Version",
    "**Date:**": "Date",
    "**Author(s):**": "Author(s)",
    "**Status:**": "Status",
}

REQUIRED_SECTIONS = {
    "1. Project Overview",
    "2. Architectural Decisions",
    "3. System Context & High-Level Architecture",
    "4. System Components",
    "5. Data Flow & Integration Patterns",
    "6. Security Architecture",
    "7. Testing Strategy",
    "8. Observability",
    "9. DevOps & Deployment",
    "10. Reliability & Disaster Recovery",
    "11. Cost & Operational Considerations",
    "12. Risks, Assumptions & Constraints",
    "13. Appendix",
}

REQUIRED_SUBSECTIONS = {
    "1. Project Overview": {
        "1.1 Purpose & Business Context",
        "1.2 Scope",
        "1.3 Definitions & Acronyms",
    },
    "2. Architectural Decisions": {
        "2.1 Architecture Style",
        "2.2 Key Architecture Decision Records (ADRs)",
    },
    "3. System Context & High-Level Architecture": {
        "3.1 System Context",
        "3.2 Architecture Diagram",
    },
    "4. System Components": {
        "4.1 Project Structure Contract",
        "4.2 Frontend Layer",
        "4.3 API Layer",
        "4.4 Database Layer",
        "4.5 Database Client Pattern",
        "4.6 Migration Strategy",
        "4.7 Caching Strategy",
        "4.8 Service Communication",
    },
    "5. Data Flow & Integration Patterns": {
        "5.1 Primary Request Flow",
        "5.2 Asynchronous Flows",
        "5.3 Third-Party Integrations",
        "5.4 Webhook Strategy",
    },
    "6. Security Architecture": {
        "6.1 Authorization Model",
        "6.2 Authentication & Session Handling",
        "6.3 API & Network Protection",
        "6.4 Data Protection & Secrets",
        "6.5 Data Lifecycle",
    },
    "8. Observability": {
        "8.1 Error Tracking",
        "8.2 Logging",
        "8.3 Request Correlation",
        "8.4 Uptime & Alerting",
    },
    "9. DevOps & Deployment": {
        "9.1 Source Control & Branching",
        "9.2 Deployment",
        "9.3 Environments",
    },
    "11. Cost & Operational Considerations": {
        "11.1 Monthly Cost Estimate",
        "11.2 Scaling Cost Triggers",
        "11.3 Vendor Lock-in Assessment",
    },
    "12. Risks, Assumptions & Constraints": {
        "12.1 Assumptions",
        "12.2 Constraints",
        "12.3 Risks",
    },
}

VALID_STATUSES = {"Draft", "In Review", "Approved"}


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    sections = _parse_sections(lines)
    _validate_sections(sections, errors)
    _validate_subsections(lines, errors)

    return errors


def _validate_metadata(lines: list[str], errors: list[str]) -> None:
    for key, label in REQUIRED_METADATA.items():
        found = [line for line in lines if key in line]
        if not found:
            errors.append(f"metadata: missing required field '{label}'")
        else:
            value = found[0].split(key)[1].strip().strip("`")
            if not value or value.startswith("<") or value.startswith("["):
                errors.append(f"metadata.{label}: field is empty or placeholder")

    # Validate status value
    status_lines = [line for line in lines if "**Status:**" in line]
    if status_lines:
        status_val = status_lines[0].split("**Status:**")[1].strip().strip("`")
        # Status might be inline like "Draft / In Review / Approved"
        if status_val and "/" not in status_val and status_val not in VALID_STATUSES:
            errors.append(f"metadata.Status: '{status_val}' not in {VALID_STATUSES}")


def _parse_sections(lines: list[str]) -> set[str]:
    sections: set[str] = set()
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            section = line[3:].strip()
            # Normalize numbered sections (strip trailing anchors, etc.)
            sections.add(section)
    return sections


def _validate_sections(sections: set[str], errors: list[str]) -> None:
    for req in REQUIRED_SECTIONS:
        if req not in sections:
            errors.append(f"structure: missing required section '## {req}'")

    # Allow "Table of Contents" and "Failure Scenarios" as known extra subsections
    allowed = REQUIRED_SECTIONS | {"Table of Contents"}
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
            subsection = line[4:].strip()
            found_subsections[current_section].add(subsection)

    for section, required_subs in REQUIRED_SUBSECTIONS.items():
        found = found_subsections.get(section, set())
        for sub in required_subs:
            if sub not in found:
                errors.append(f"structure.{section}: missing subsection '### {sub}'")

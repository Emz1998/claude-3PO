#!/usr/bin/env python3
"""Generate PRD.md from product.json using templates."""

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_template(template_path: Path) -> str:
    """Load a template file."""
    return template_path.read_text()


def replace_placeholders(template: str, data: dict[str, Any]) -> str:
    """Replace {placeholder} with values from data dict."""
    result = template
    for key, value in data.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))
    return result


def format_list(items: list[str], indent: str = "  ") -> str:
    """Format a list of items as markdown bullet points."""
    return "\n".join(f"{indent}- {item}" for item in items)


def format_acceptance_criteria(criteria: list[dict[str, str]]) -> str:
    """Format acceptance criteria list."""
    lines = []
    for ac in criteria:
        lines.append(f"    - {ac['id']}: {ac['criteria']}")
    return "\n".join(lines)


def format_user_story(story: dict[str, Any], template: str) -> str:
    """Format a single user story."""
    ac_text = format_acceptance_criteria(story.get("acceptance_criteria", []))
    data = {
        "id": story["id"],
        "title": story["title"],
        "story": story["story"],
        "acceptance_criteria": ac_text,
    }
    return replace_placeholders(template, data)


def format_risk(risk: dict[str, str], template: str) -> str:
    """Format a single risk."""
    return replace_placeholders(template, risk)


def format_feature(feature: dict[str, Any], templates: dict[str, str]) -> str:
    """Format a single feature."""
    # Format user stories
    user_stories = []
    for story in feature.get("user_stories", []):
        user_stories.append(format_user_story(story, templates["user_story"]))
    user_stories_section = "\n".join(user_stories)

    # Format functional requirements
    func_reqs = feature.get("requirements", {}).get("functional", [])
    func_lines = [f"- {r['id']}: {r['description']}" for r in func_reqs]
    functional_requirements = "\n".join(func_lines) if func_lines else "- None"

    # Format non-functional requirements
    nfunc_reqs = feature.get("requirements", {}).get("non_functional", [])
    nfunc_lines = [f"- {r['id']}: {r['description']}" for r in nfunc_reqs]
    non_functional_requirements = "\n".join(nfunc_lines) if nfunc_lines else "- None"

    # Format dependencies
    deps = feature.get("dependencies", [])
    dep_lines = [
        f"- {d['id']}: {d['dependency']} - Assumption: {d['assumption']}" for d in deps
    ]
    dependencies_section = "\n".join(dep_lines) if dep_lines else "- None"

    # Format risks
    risks = []
    for risk in feature.get("risks", []):
        risks.append(format_risk(risk, templates["risk"]))
    risks_section = "\n".join(risks) if risks else "- None"

    # Format success criteria
    sc = feature.get("success_criteria", [])
    sc_lines = [f"- {s['id']}: {s['title']} - {s['description']}" for s in sc]
    success_criteria_section = "\n".join(sc_lines) if sc_lines else "- None"

    data = {
        "id": feature["id"],
        "name": feature["name"],
        "description": feature["description"],
        "user_stories_section": user_stories_section,
        "functional_requirements": functional_requirements,
        "non_functional_requirements": non_functional_requirements,
        "dependencies_section": dependencies_section,
        "risks_section": risks_section,
        "success_criteria_section": success_criteria_section,
    }
    return replace_placeholders(templates["feature"], data)


def format_version(version: dict[str, Any], templates: dict[str, str]) -> str:
    """Format a single version."""
    features = []
    for feature in version.get("features", []):
        features.append(format_feature(feature, templates))
    features_section = "\n".join(features) if features else "_No features defined_"

    data = {
        "version": version["version"],
        "release_date": version["release_date"],
        "status": version["status"],
        "features_section": features_section,
    }
    return replace_placeholders(templates["version"], data)


def generate_prd(product_data: dict[str, Any], templates: dict[str, str]) -> str:
    """Generate the full PRD markdown from product data."""
    overview = product_data.get("overview", {})
    metadata = product_data.get("metadata", {})

    # Format solutions list
    solutions = overview.get("solutions", [])
    solutions_list = format_list(solutions)

    # Format goals list
    goals = overview.get("goals", [])
    goals_list = format_list(goals)

    # Format tech stack
    tech_stack = product_data.get("tech_stack", [])
    tech_stack_list = "\n".join(f"- {tech}" for tech in tech_stack)

    # Format all versions
    versions = []
    for version in product_data.get("versions", []):
        versions.append(format_version(version, templates))
    versions_section = "\n".join(versions)

    # Extract product name (first part before " - ")
    full_name = overview.get("name", "Product")
    product_name = full_name.split(" - ")[0] if " - " in full_name else full_name

    data = {
        "product_name": product_name,
        "current_version": product_data.get("current_version", "v0.1.0"),
        "stable_version": product_data.get("stable_version", "v1.0.0"),
        "last_updated": metadata.get("last_updated", ""),
        "updated_by": metadata.get("updated_by", ""),
        "overview_name": overview.get("name", ""),
        "overview_type": overview.get("type", ""),
        "overview_elevator_pitch": overview.get("elevator_pitch", ""),
        "overview_industry_problem": overview.get("industry_problem", ""),
        "solutions_list": solutions_list,
        "goals_list": goals_list,
        "tech_stack_list": tech_stack_list,
        "versions_section": versions_section,
    }
    return replace_placeholders(templates["prd"], data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PRD.md from PRD.json")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="project/product/PRD.json",
        help="Input JSON file path (default: project/product/PRD.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="project/product/PRD.md",
        help="Output markdown file path (default: project/product/PRD.md)",
    )
    parser.add_argument(
        "-t",
        "--templates",
        type=str,
        default=None,
        help="Templates directory (default: .claude/skills/product-management/templates)",
    )
    args = parser.parse_args()

    # Resolve paths relative to project root
    script_dir = Path(__file__).parent
    project_root = (
        script_dir.parent.parent.parent.parent
    )  # .claude/skills/product-management/scripts -> project root

    input_path = project_root / args.input
    output_path = project_root / args.output

    if args.templates:
        templates_dir = Path(args.templates)
    else:
        templates_dir = project_root / ".claude/skills/product-management/templates"

    # Load product data
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return

    with open(input_path, "r") as f:
        product_data = json.load(f)

    # Load templates
    templates = {
        "prd": load_template(templates_dir / "PRD.md"),
        "version": load_template(templates_dir / "version.md"),
        "feature": load_template(templates_dir / "feature.md"),
        "user_story": load_template(templates_dir / "user_story.md"),
        "risk": load_template(templates_dir / "risk.md"),
    }

    # Generate PRD
    prd_content = generate_prd(product_data, templates)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_path, "w") as f:
        f.write(prd_content)

    print(f"PRD generated: {output_path}")


if __name__ == "__main__":
    main()

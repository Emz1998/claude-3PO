"""plans.py — Extract structured data from a plan markdown file.

Plan files follow a fixed H2 layout (``## Dependencies``, ``## Tasks``,
``## Files to Create/Modify``). These helpers pull the bullets / rows out of
those sections so guards and resolvers don't re-implement the markdown walk.
"""

from .markdown import (
    extract_bullet_items,
    extract_md_sections,
    extract_section_map,
    extract_table,
)


def _extract_section_bullets(content: str, heading: str) -> list[str]:
    """Extract bullets from the ``## heading`` section in *content*.

    Example:
        >>> _extract_section_bullets("## Tasks\\n- a\\n- b", "Tasks")
        ['a', 'b']
    """
    return extract_bullet_items(extract_section_map(content, 2).get(heading, ""))


def extract_plan_dependencies(content: str) -> list[str]:
    """
    Parse the ``## Dependencies`` bullet list from a plan file.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: Package names; empty if the section is missing.

    Example:
        >>> extract_plan_dependencies("## Dependencies\\n- requests\\n- pytest")
        ['requests', 'pytest']
    """
    return _extract_section_bullets(content, "Dependencies")


def extract_plan_tasks(content: str) -> list[str]:
    """
    Parse the ``## Tasks`` bullet list from a plan file.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: Task subjects; empty if the section is missing.

    Example:
        >>> extract_plan_tasks("## Tasks\\n- Write tests\\n- Implement")
        ['Write tests', 'Implement']
    """
    return _extract_section_bullets(content, "Tasks")


def extract_plan_files_to_modify(content: str) -> list[str]:
    """
    Extract file paths from the plan's ``Files to Create/Modify`` table.

    Accepts either ``Files to Create/Modify`` or the legacy ``Files to Modify``
    heading. Expects an ``Action | Path`` table and returns the Path column.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: File paths in table order; empty if the section or table
        is missing.

    Example:
        >>> md = "## Files to Modify\\n| Action | Path |\\n|---|---|\\n| edit | a.py |"
        >>> extract_plan_files_to_modify(md)
        ['a.py']
    """
    sections = extract_md_sections(content, 2)
    for name, body in sections:
        if name.strip() in ("Files to Create/Modify", "Files to Modify"):
            table = extract_table(body)
            if len(table) < 2:  # header + at least 1 data row
                return []
            # Skip header row, extract Path column (index 1)
            return [row[1].strip() for row in table[1:] if len(row) > 1 and row[1].strip()]
    return []

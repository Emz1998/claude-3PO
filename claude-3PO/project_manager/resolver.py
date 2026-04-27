"""Rule-based status resolver for the backlog.

``project.json`` owns the truth, but derived statuses (e.g. Ready once
blockers clear, In review once every task is Done) need to be computed.
This module is the pure rule engine — no file I/O, no network — so both
the ``watch`` watcher and any future in-process caller can drive it.

The engine iterates each rule to a fixed point so cascades (Story → Done
unblocks downstream Backlog items on the next pass) resolve in one call.
"""
from __future__ import annotations

from .manager import (
    VALID_TRANSITIONS,
    build_status_map_from_backlog,
    is_unblocked,
)


def resolve(backlog: dict) -> bool:
    """Apply every rule to ``backlog`` until no rule fires again.

    Mutates ``backlog`` in place. The loop reruns every rule whenever any
    rule changed a status so dependent rules see the fresh state — this
    is what makes cascades (blocker goes Done → dependent promotes) work.

    Args:
        backlog (dict): Parsed ``project.json``. Missing ``stories`` key is
            treated as an empty backlog.

    Returns:
        bool: ``True`` if any status changed, else ``False``.

    SideEffect:
        Mutates ``backlog["stories"][*]["status"]`` and
        ``backlog["stories"][*]["tasks"][*]["status"]`` for items the rules
        fire on.

    Example:
        >>> resolve({"stories": [{"id": "SK-1", "status": "Backlog",
        ...                       "blocked_by": [], "tasks": []}]})  # doctest: +SKIP
        Return: True
        SideEffect:
            SK-1 status Backlog -> Ready
    """
    any_changed = False
    # Fixed-point loop: re-run every rule until a full pass is a no-op.
    while _one_pass(backlog):
        any_changed = True
    return any_changed


def _one_pass(backlog: dict) -> bool:
    """Run each rule once; return True if any rule produced a change.

    Args:
        backlog (dict): Backlog mutated in place.

    Returns:
        bool: True if any rule changed a status this pass.

    Example:
        >>> _one_pass({"stories": []})  # doctest: +SKIP
        Return: False
    """
    # Each rule short-circuits-OR is intentional: we want *all* rules to
    # fire each pass, not just the first one that changes something.
    changed = False
    changed = _promote_unblocked(backlog) or changed
    changed = _promote_story_in_review(backlog) or changed
    return changed


def _promote_unblocked(backlog: dict) -> bool:
    """Promote ``Backlog`` items whose dependencies are all ``Done`` to ``Ready``.

    Applies to both stories and tasks. Honours :data:`VALID_TRANSITIONS`
    implicitly — ``Backlog → Ready`` is the only allowed target.

    Args:
        backlog (dict): Backlog mutated in place.

    Returns:
        bool: True if at least one item was promoted.

    Example:
        >>> _promote_unblocked({"stories": [{"id": "SK-1", "status": "Backlog",
        ...                                  "blocked_by": [], "tasks": []}]})  # doctest: +SKIP
        Return: True
    """
    # Build the {id: status} map once per pass — tasks can depend on stories
    # and siblings, so we need the global view.
    status_by_id = build_status_map_from_backlog(backlog)
    changed = False
    # Iterate with parent context so tasks can be gated on parent-story status.
    for item, parent_story in _iter_items_with_parent(backlog):
        if _should_promote_to_ready(item, status_by_id, parent_story):
            item["status"] = "Ready"
            changed = True
    return changed


def _should_promote_to_ready(
    item: dict, status_by_id: dict[str, str], parent_story: dict | None
) -> bool:
    """Return True if *item* is eligible for ``Backlog → Ready``.

    Tasks are additionally gated on their parent story: a child task cannot
    become "workable" (`Ready`) while its owning story is still `Backlog` —
    otherwise the listing would advertise work that belongs to a story no
    one has committed to yet. Stories themselves pass ``parent_story=None``
    and skip that gate.

    Args:
        item (dict): Story or task being considered.
        status_by_id (dict[str, str]): Global id → status map.
        parent_story (dict | None): Owning story for a task, or ``None``
            when *item* is itself a story.

    Returns:
        bool: True iff item is in ``Backlog``, every blocker is ``Done``,
            and (for tasks) its parent story has left ``Backlog``.

    Example:
        >>> _should_promote_to_ready(
        ...     {"status": "Backlog", "blocked_by": []}, {}, None
        ... )  # doctest: +SKIP
        Return: True
    """
    # Must start from Backlog — anything else would violate VALID_TRANSITIONS.
    if item.get("status") != "Backlog":
        return False
    # Blocker gate applies to stories and tasks alike.
    if not is_unblocked(item.get("blocked_by", []), status_by_id):
        return False
    # Parent-story gate: only tasks carry a parent, so the check is a no-op
    # for stories. Parent must have advanced past `Backlog` before we
    # advertise its children as work-ready.
    if parent_story is not None and parent_story.get("status") == "Backlog":
        return False
    return True


def _promote_story_in_review(backlog: dict) -> bool:
    """Move stories from ``In progress`` to ``In review`` once every task is ``Done``.

    Stories with no tasks are skipped — a zero-task story would otherwise
    trip the rule the moment someone manually moves it into In progress.

    Args:
        backlog (dict): Backlog mutated in place.

    Returns:
        bool: True if at least one story was promoted.

    Example:
        >>> _promote_story_in_review({"stories": [{"id": "SK-1", "status":
        ...     "In progress", "tasks": [{"status": "Done"}]}]})  # doctest: +SKIP
        Return: True
    """
    changed = False
    for story in backlog.get("stories", []):
        if _all_tasks_done(story) and _can_transition(story, "In review"):
            story["status"] = "In review"
            changed = True
    return changed


def _all_tasks_done(story: dict) -> bool:
    """Return True if *story* has at least one task and all are ``Done``.

    Args:
        story (dict): Story record.

    Returns:
        bool: True only when tasks exist and every one is Done.

    Example:
        >>> _all_tasks_done({"tasks": [{"status": "Done"}]})  # doctest: +SKIP
        Return: True
    """
    tasks = story.get("tasks", [])
    if not tasks:
        return False
    return all(t.get("status") == "Done" for t in tasks)


def _can_transition(item: dict, target: str) -> bool:
    """Guard against rules producing an illegal VALID_TRANSITIONS move.

    Args:
        item (dict): Item whose ``status`` is the current state.
        target (str): Proposed new status.

    Returns:
        bool: True iff ``current → target`` is listed in VALID_TRANSITIONS.

    Example:
        >>> _can_transition({"status": "In progress"}, "In review")  # doctest: +SKIP
        Return: True
    """
    return target in VALID_TRANSITIONS.get(item.get("status", ""), set())


def _iter_items_with_parent(backlog: dict):
    """Yield ``(item, parent_story_or_None)`` tuples for every story and task.

    Threading the parent alongside each task lets callers apply parent-aware
    rules (e.g. "don't promote a task whose story is still Backlog") without
    re-walking the tree or looking up the parent by id. Stories yield a
    ``None`` parent since they sit at the top of the backlog.

    Args:
        backlog (dict): Parsed backlog.

    Yields:
        tuple[dict, dict | None]: ``(story, None)`` for every story, then
            ``(task, story)`` for each task nested under that story.

    Example:
        >>> list(_iter_items_with_parent(
        ...     {"stories": [{"id": "A", "tasks": [{"id": "T"}]}]}
        ... ))  # doctest: +SKIP
        Return: [({"id": "A", ...}, None), ({"id": "T"}, {"id": "A", ...})]
    """
    for story in backlog.get("stories", []):
        # Story first (parent=None), then its children paired with the story.
        yield story, None
        for task in story.get("tasks", []):
            yield task, story

"""ordering.py — Pure helpers for enforcing strict forward-by-one sequencing.

Extracted from :class:`PhaseGuard` so other guards (or dispatchers) can reuse
the same skip/backward/repeat detection without taking a dependency on the
guard class. Purely functional — no filesystem, no state, no side effects.
"""


def check_item_in_order(item: str, order: list[str], label: str) -> None:
    """
    Confirm ``item`` appears in ``order``.

    Args:
        item (str): Item to check.
        order (list[str]): Reference ordered list.
        label (str): Human-readable label used in the error message.

    Raises:
        ValueError: If ``item`` is not in ``order``.

    Example:
        >>> check_item_in_order("plan", ["plan", "code"], "phase")
        >>> # Raises ValueError when the item is missing from order.
    """
    if item not in order:
        raise ValueError(f"Invalid {label} '{item}'")


def validate_order(prev: str | None, next_item: str, order: list[str]) -> str:
    """
    Enforce strict forward-by-one ordering of items against ``order``.

    Used by guards for both phase ordering (with current-phase as ``prev``) and
    skill ordering. The first transition (``prev is None``) must hit ``order[0]``;
    subsequent transitions must advance by exactly one position — equal index
    means "already entered", lower index means "going backwards", higher than
    +1 means "skipping items".

    Args:
        prev (str | None): Previous item, or ``None`` for the first transition.
        next_item (str): Item being transitioned to.
        order (list[str]): Reference order.

    Returns:
        str: Success message describing the allowed transition.

    Raises:
        ValueError: If the transition violates the ordering invariants.

    Example:
        >>> validate_order(None, "plan", ["plan", "code"])
        "Allowed to start with 'plan'"
        >>> validate_order("plan", "code", ["plan", "code"])
        "Phase is allowed to transition to 'code'"
    """
    check_item_in_order(next_item, order, "next item")

    # First transition has no prev — force callers to hit the canonical start.
    if prev is None:
        if next_item != order[0]:
            raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")
        return f"Allowed to start with '{order[0]}'"

    check_item_in_order(prev, order, "previous item")

    prev_idx = order.index(prev)
    next_idx = order.index(next_item)

    # Three distinct error messages so the caller can tell whether the user is
    # re-invoking, going backwards, or skipping ahead.
    if next_idx == prev_idx:
        raise ValueError(
            f"Cannot re-invoke '{prev}'. The phase has already been entered — "
            f"advance to the next phase, or complete its tasks instead of restarting it."
        )
    if next_idx < prev_idx:
        raise ValueError(f"Cannot go backwards from '{prev}' to '{next_item}'")
    if next_idx > prev_idx + 1:
        skipped = order[prev_idx + 1 : next_idx]
        raise ValueError(f"Must complete {skipped} before '{next_item}'")

    return f"Phase is allowed to transition to '{next_item}'"

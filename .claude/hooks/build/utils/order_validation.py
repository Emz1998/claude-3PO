def validate_order(
    prev_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order."""
    if next_item not in order:
        return False, f"Invalid next item '{next_item}'"

    if prev_item is None:
        if next_item == order[0]:
            return True, ""
        return False, f"Must start with '{order[0]}', not '{next_item}'"

    if prev_item not in order:
        return False, f"Invalid previous item: '{prev_item}'"

    prev_idx = order.index(prev_item)
    next_idx = order.index(next_item)

    if next_idx < prev_idx:
        return False, f"Cannot go backwards from '{prev_item}' to '{next_item}'"

    if next_idx > prev_idx + 1:
        skipped = order[prev_idx + 1 : next_idx]
        return False, f"Must complete {skipped} before '{next_item}'"

    return True, ""

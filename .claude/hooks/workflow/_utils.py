#!/usr/bin/env python3
"""Phase transition guard hook for workflow enforcement."""

import json
import sys
from pathlib import Path
from typing import Any


def validate_order(
    current_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate phase transition based on workflow configuration."""
    if next_item not in order:
        return False, f"Invalid next item: '{next_item}'"
    if current_item is None:
        if next_item == order[0]:
            return True, ""
        return False, f"Must start with '{order[0]}', not '{next_item}'"
    if current_item not in order:
        return False, f"Invalid current item: '{current_item}'"
    current_idx = order.index(current_item)
    new_idx = order.index(next_item)
    if new_idx < current_idx:
        return False, f"Cannot go backwards from '{current_item}' to '{next_item}'"
    if new_idx > current_idx + 1:
        skipped = order[current_idx + 1 : new_idx]
        return False, f"Must complete {skipped} before '{next_item}'"
    return True, ""


def get_last_item(order: list[str]) -> str:
    return order[-1]

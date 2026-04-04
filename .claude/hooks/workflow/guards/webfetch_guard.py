"""webfetch_guard.py — Domain whitelist validation for WebFetch.

Only enforced when workflow_active == True.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import SAFE_DOMAINS
from workflow.session_store import SessionStore


def _is_safe_domain(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host:
            return False
        for domain in SAFE_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a WebFetch invocation against the domain whitelist.

    Only enforced when workflow_active == True.
    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    url = hook_input.get("tool_input", {}).get("url", "")
    if not _is_safe_domain(url):
        return (
            "block",
            f"Blocked: domain not in whitelist. URL must be from approved domains ({', '.join(SAFE_DOMAINS[:5])}...). Use an allowed domain or add this one to SAFE_DOMAINS.",
        )
    return "allow", ""

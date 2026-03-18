def get_review_dir(session_id: str) -> str:
    return f".claude/sessions/session_{session_id}/review/review_report.md"

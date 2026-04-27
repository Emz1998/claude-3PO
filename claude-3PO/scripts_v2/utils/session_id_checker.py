from lib.store import StateStore


def session_id_matches(session_id: str) -> tuple[bool, str]:
    state_store = StateStore()
    state_session_id = state_store.session_id
    if session_id != state_session_id:
        return False, "Session ID does not match state session ID"
    return True, "Session ID matches state session ID"

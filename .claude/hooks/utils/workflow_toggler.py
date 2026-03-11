import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from workflow.state_store import StateStore
from workflow.config import get as cfg

STATE_PATH = Path(cfg("paths.workflow_state"))


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("enable", nargs="?", help="Enable the workflow")
    parser.add_argument("disable", nargs="?", help="Disable the workflow")
    args = parser.parse_args()
    current_state = StateStore(STATE_PATH).get("workflow_active")

    if not any(vars(args).values()):
        if current_state is False:
            StateStore(STATE_PATH).set("workflow_active", True)
        else:
            StateStore(STATE_PATH).set("workflow_active", False)
    if args.enable:
        StateStore(STATE_PATH).set("workflow_active", True)
    elif args.disable:
        StateStore(STATE_PATH).set("workflow_active", False)

    new_state = StateStore(STATE_PATH).get("workflow_active")

    print(
        f"Workflow succesfully toggled to {"enabled" if new_state is True else 'disabled'}",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()

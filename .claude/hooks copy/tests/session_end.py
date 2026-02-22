import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, write_file, read_file  # type: ignore


def main() -> None:
    hook_input = read_stdin_json()

    file_path = Path("input-schemas/session_end.log")
    if not Path(file_path).parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(file_path), json.dumps(hook_input, indent=4))


if __name__ == "__main__":
    main()

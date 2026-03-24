import sys
import json


def read_stdin_json() -> dict:
    return json.loads(sys.stdin.read())


def main() -> None:
    raw_input = read_stdin_json()

    session_id = raw_input["session_id"]

    output = {"systemMessage": f"\n\nSession ID: {session_id}"}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()

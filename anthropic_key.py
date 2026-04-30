#!/usr/bin/env python3


from pathlib import Path
import json


def get_anthropic_key():
    credentials_path = Path("/home/emhar/.claude/.credentials.json").read_text()
    return json.loads(credentials_path)["claudeAiOauth"]["accessToken"]


def main():
    print(get_anthropic_key())


if __name__ == "__main__":
    main()

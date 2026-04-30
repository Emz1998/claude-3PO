"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from pathlib import Path
from utils.hook import Hook  # type: ignore

QUESTIONS_PATH = Path.cwd() / "claude-3PO" / "questions.txt"


def validate_question(question: str, questions: list[str]) -> None:
    if question in questions:
        return
    raise ValueError(f"Question {question} is not valid")


def parse_questions(content: str) -> list[str]:
    splitted_content = content.split("\n")
    if not splitted_content:
        return []
    return [line.strip() for line in splitted_content if line.strip()]


def load_questions(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        content = path.read_text()
        return parse_questions(content)
    except Exception as e:
        Hook.block(f"Error loading questions from {path}: {e}")
        return []


def main() -> None:

    hook_input = Hook.read_stdin()
    question = hook_input.get("tool_input", {}).get("question", "")

    questions = load_questions(QUESTIONS_PATH)
    if not questions:
        Hook.system_message("No questions found")

    if not question:
        Hook.system_message("Question is required")
    try:
        validate_question(question, questions)
    except ValueError as e:
        Hook.block(str(e))


if __name__ == "__main__":
    main()

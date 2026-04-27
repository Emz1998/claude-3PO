from utils.agent_cli_v2 import build_argv, run_headless_parallel, ClaudeConfig, CodexConfig, parse_agent_response  # type: ignore
from utils.hook import Hook  # type: ignore
from lib.conformance_check import template_conformance_check, verdict_present, scores_present  # type: ignore
from utils.review_scores import extract_scores, scores_valid, scores_passing, extract_verdict  # type: ignore
import os
import subprocess
from pathlib import Path
from typing import Literal, Any
import json

# Test mode short-circuits agent invocations so the workflow can be exercised
# end-to-end without burning agent runs. Reports are generated from the
# templates with passing scores so downstream gating still flips to --approve.
TEST_MODE = os.environ.get("CODE_REVIEW_TEST_MODE") == "1"
TEST_MODE_PR_BODY = "Test mode: mock review (agents skipped)."

PROJECTS_DIR = Path.cwd() / "projects"
CLAUDE_3PO_DIR = PROJECTS_DIR / "claude-3PO"
CODE_REVIEW_DIR = PROJECTS_DIR / "code-review"
# Templates ship with the repo, not under PROJECTS_DIR (which is for runtime artifacts).
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "code_review"

REPORT_PATHS = [
    TEMPLATES_DIR / "requirements_review.md",
    TEMPLATES_DIR / "code_review.md",
    TEMPLATES_DIR / "security_review.md",
]

REVIEW_CONFIG_MAP = {
    "security_review": {
        "owner": "claude",
        "prompt": "/security-review",
        "template": TEMPLATES_DIR / "security_review_template.md",
    },
    "code_review": {
        "owner": "claude",
        "prompt": "/code-review",
        "template": TEMPLATES_DIR / "code_review_template.md",
    },
    "requirements_review": {
        "owner": "codex",
        "prompt": "/requirements-review",
        "template": TEMPLATES_DIR / "requirements_review_template.md",
    },
}


def view_pr_content(pr_number: int) -> str:
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number)], check=True, capture_output=True, text=True
    )
    return result.stdout


def get_pr_number() -> int:
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number", "-q", ".number"],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def check_review_output(result: str, template: str) -> tuple[bool, str]:
    # template conformance gates score validation; the diff feeds back to the agent
    ok, diff = template_conformance_check(result, template)
    if not ok:
        return False, diff
    scores = extract_scores(result)
    if not scores_valid(scores):
        return False, "Scores are not valid"
    return True, "Output is valid"


def check_validation_output(result: str) -> tuple[bool, str]:
    verdict = extract_verdict(result)
    if verdict not in ["Pass", "Fail"]:
        return False, "Verdict is not valid"
    return True, "Verdict is valid"


def generate_pr_review_content(review_paths: list[Path]) -> str | None:
    relative_review_paths = [
        str(review_path.relative_to(CODE_REVIEW_DIR)) for review_path in review_paths
    ]
    parsed_reports_paths = f" ".join(relative_review_paths)
    prompt = f"/create-pr-review {parsed_reports_paths}"
    claude_argv = build_argv(prompt, ClaudeConfig(model="haiku", output_format="json"))
    success, result = run_headless_parallel([claude_argv])
    if not success:
        return None
    # result[0] is the JSON envelope; extract the agent's text for the PR-review body
    return get_claude_result(result[0])


def decide_pr_review_action(review_paths: list[Path]) -> str:
    # one failing review (either score below threshold) flips the PR to request-changes;
    # only an all-clear sweep gets the approve action
    for path in review_paths:
        scores = extract_scores(path.read_text())
        ok, _ = scores_passing(scores)
        if not ok:
            return "--request-changes"
    return "--approve"


def create_pr_review() -> bool:
    body = generate_pr_review_content(REPORT_PATHS)
    if body is None:
        return False
    # saved review files live next to CODE_REVIEW_DIR, named after their config key
    saved_paths = [CODE_REVIEW_DIR / f"{key}.md" for key in REVIEW_CONFIG_MAP]
    action = decide_pr_review_action(saved_paths)
    pr_number = get_pr_number()
    subprocess.run(
        ["gh", "pr", "review", str(pr_number), action, "--body", body],
        check=True,
        capture_output=True,
        text=True,
    )
    return True


def save_code_review_report(output: str) -> bool:
    report_file = CODE_REVIEW_DIR / "report.md"
    report_file.write_text(output)
    return True


def run_subprocess_popen(argv: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def get_codex_session_id(stdout: str) -> str:
    parsed = parse_agent_response(stdout)
    return parsed[0]


def get_claude_session_id(stdout: str) -> str:
    json_output = json.loads(stdout)
    return json_output["session_id"]


def get_session_id(stdout: str, owner: Literal["codex", "claude"]) -> str:
    if owner == "codex":
        return get_codex_session_id(stdout)
    return get_claude_session_id(stdout)


def get_claude_result(stdout: str) -> str:
    # claude --output-format json wraps the agent reply in a result field
    return json.loads(stdout)["result"]


def get_codex_result(stdout: str) -> str:
    # codex JSONL stream: parse_agent_response collapses to (thread_id, text, raw)
    _, text, _ = parse_agent_response(stdout)
    return text


def get_result(stdout: str, owner: Literal["codex", "claude"]) -> str:
    if owner == "codex":
        return get_codex_result(stdout)
    return get_claude_result(stdout)


def build_sub_config(owner: str) -> Any:
    # owner picks the agent CLI flavor; both wrappers share the same json_output contract
    if owner == "codex":
        # codex `--json` is a real flag (JSONL stream); claude uses `--output-format json`
        return CodexConfig(model="codex", json_output=True)
    if owner == "claude":
        return ClaudeConfig(model="haiku", output_format="json")
    raise ValueError(f"Unknown owner: {owner}")


def start_review_processes(
    pr_content: str, config: dict[str, Any]
) -> dict[str, tuple[subprocess.Popen, Literal["codex", "claude"]]]:
    procs: dict[str, tuple[subprocess.Popen, Literal["codex", "claude"]]] = {}
    for key, cfg in config.items():
        # spawn each review concurrently; we wait on them in collect_review_results
        argv = build_argv(
            f"{cfg['prompt']} {pr_content}", build_sub_config(cfg["owner"])
        )
        procs[key] = (run_subprocess_popen(argv), cfg["owner"])
    return procs


def collect_review_results(
    procs: dict[str, tuple[subprocess.Popen, Literal["codex", "claude"]]],
) -> dict[str, tuple[int, str, str, str]]:
    # Per-key tuple is (returncode, agent_text, stderr, session_id) — note slot 1 is the
    # extracted review text, NOT the raw JSON envelope. Downstream (correct_one,
    # save_review_report) consumes review text directly.
    results: dict[str, tuple[int, str, str, str]] = {}
    for key, (p, owner) in procs.items():
        stdout, stderr = p.communicate()
        content = get_result(stdout, owner)
        session_id = get_session_id(stdout, owner)
        results[key] = (p.returncode, content, stderr, session_id)
    return results


def run_headless_review(
    pr_content: str, config: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Start all commands in parallel, wait for all, return dict of (returncode, stdout, stderr, session_id)."""
    procs = start_review_processes(pr_content, config)
    results = collect_review_results(procs)
    if any(rc != 0 for rc, _, _, _ in results.values()):
        return False, {}
    return True, results


def correct_one(key: str, results: dict[str, Any], template: str) -> bool:
    # results[key][1] is already the extracted agent text (set in collect_review_results)
    ok, diff = check_review_output(results[key][1], template)
    while not ok:
        cfg = ClaudeConfig(
            model="haiku", session_id=results[key][3], output_format="json"
        )
        success, result = run_headless_parallel([build_argv(diff, cfg)])
        if not success:
            return False
        # re-prompt response is a fresh JSON envelope; pull out the text before checking
        ok, diff = check_review_output(get_claude_result(result[0]), template)
    return True


def run_correction(results: dict[str, Any], config: dict[str, Any]) -> bool:
    for key, cfg in config.items():
        template = cfg["template"].read_text()
        if not correct_one(key, results, template):
            return False
    return True


def save_review_report(key: str, output: str) -> None:
    # one file per review key (e.g. code_review.md) — REPORT_PATHS mirrors these names
    (CODE_REVIEW_DIR / f"{key}.md").write_text(output)


def run_review() -> None:
    pr_number = get_pr_number()
    pr_content = view_pr_content(pr_number)
    success, results = run_headless_review(pr_content, REVIEW_CONFIG_MAP)
    if not success:
        print("Failed to run review")
        return
    if not run_correction(results, REVIEW_CONFIG_MAP):
        print("Correction loop failed")
        return
    for key, (_, stdout, _, _) in results.items():
        save_review_report(key, stdout)


def make_mock_review(template_path: Path) -> str:
    # Templates ship with `Confidence Score: 0` / `Quality Score: 0`; bump both to
    # 90 so scores_valid passes (≤100) and scores_passing passes (≥80 threshold).
    content = template_path.read_text()
    content = content.replace("Confidence Score: 0", "Confidence Score: 90")
    content = content.replace("Quality Score: 0", "Quality Score: 90")
    return content


def run_review_test_mode() -> None:
    # bypass spawn/correct entirely — write the mock straight to each report file
    for key, cfg in REVIEW_CONFIG_MAP.items():
        save_review_report(key, make_mock_review(cfg["template"]))


def create_pr_review_test_mode() -> bool:
    # static body avoids the /create-pr-review agent call; gh posts as usual
    saved_paths = [CODE_REVIEW_DIR / f"{key}.md" for key in REVIEW_CONFIG_MAP]
    action = decide_pr_review_action(saved_paths)
    pr_number = get_pr_number()
    subprocess.run(
        ["gh", "pr", "review", str(pr_number), action, "--body", TEST_MODE_PR_BODY],
        check=True, capture_output=True, text=True,
    )
    return True


def main() -> None:
    if TEST_MODE:
        run_review_test_mode()
        create_pr_review_test_mode()
        return
    run_review()
    create_pr_review()


if __name__ == "__main__":
    main()

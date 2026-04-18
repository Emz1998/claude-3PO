# Scripts — Workflow Hook System

Guardrail engine that enforces phase-based rules for the `claude-3PO` Claude Code plugin. Every Claude Code lifecycle event is routed through a dispatcher, validated against the current phase, recorded to a session-scoped state file, and resolved to decide whether the workflow advances.

## Architecture

```
Claude Code event (stdin JSON)
        │
        ▼
  dispatchers/*.py        ── entry points (one per hook event)
        │
        ├─► guardrails/*.py   ── validate ("allow" | "block")
        ├─► utils/recorder.py ── write raw data into state
        └─► utils/resolver.py ── evaluate state, complete phases,
                                  auto-start next phase,
                                  mark workflow complete
        │
        ▼
  stdout JSON (permissionDecision, continue:false, systemMessage, …)
```

All modules import from a shared `lib/` (I/O, extractors, parsers, state, violations, scoring, paths, shell, parallel-check, specs validation), `config/` (declarative phase/agent/path config — `get_config()` returns a process-wide cached `Config()`), `constants/` (command whitelists, file patterns, phase sets, markers, paths), and `models/` (Pydantic schema for state, batch entries, and story items).

**Layering rule:** `guardrails/*` never imports from `utils/*`, and `utils/recorder.py` never imports from `guardrails/*`. Pure helpers live in `lib/`; orchestration lives in `dispatchers/`.

## Workflow types

Three workflows are wired in `config/config.json`. A phase belongs to a workflow when its `workflows` array contains the workflow name.

| Workflow    | Purpose                                | Phase track                                                                                                                                                    |
| ----------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `build`     | End-to-end feature build from scratch  | clarify (auto) → explore → research → decision → plan → plan-review → create-tasks → write-tests → test-review → write-code → quality-check → code-review → pr-create → ci-check → write-report |
| `implement` | Execute an existing story from a backlog | explore → research → plan → plan-review → create-tasks → write-tests → tests-review → write-code → validate → code-review → pr-create → ci-check → write-report |
| `specs`     | Produce product/architecture artifacts   | vision → strategy → decision → architect → backlog                                                                                                             |

Each phase entry carries capability flags (`read_only`, `code_write`, `code_edit`, `docs_write`, `docs_edit`, `auto`, `checkpoint`) and an optional `agent` + `agent_count`. The `Config` class derives phase lists from those flags — no separate enum is maintained.

## Entry points (`dispatchers/`)

Wired in `hooks/hooks.json`. Each reads Claude's JSON from stdin, short-circuits when the session has no active workflow, then delegates.

| File                            | Hook event           | Role                                                                                                                  |
| ------------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `pre_tool_use.py`               | `PreToolUse`         | Looks up `TOOL_GUARDS[tool_name]` and emits `permissionDecision: "deny"` on block. Logs every block to `violations.md`. |
| `post_tool_use.py`              | `PostToolUse`        | `Recorder.record(...)` then `resolve(...)` to auto-complete phases and auto-start the next.                            |
| `post_tool_use_failure.py`      | `PostToolUseFailure` | Bash-only. Records test execution even when the command exits non-zero (TDD-style failing tests still progress phase). |
| `subagent_start.py`             | `SubagentStart`      | Registers `Agent(name, status="in_progress", tool_use_id=agent_id)` so agent counts and completion are tracked.        |
| `subagent_stop.py`              | `SubagentStop`       | Marks the agent `completed`. For review/specs phases, validates the report (`AgentReportGuard`) and runs a **3-strike retry cap**: attempts 1–2 block the subagent from stopping (`exit 2`) with an actionable, template-aware stderr so the agent can course-correct; attempt 3 marks the agent `status="failed"`, logs a single `SubagentStop` violation, and releases the subagent (`exit 0`). Triggers checkpoint on plan-review pass via `Hook.discontinue`. |
| `task_created.py`               | `TaskCreated`        | Validates task subject against `state.tasks` (build) or project tasks (implement) and records the link.                |
| `task_completed.py`             | `TaskCompleted`      | Implement workflow only: marks the child subtask done; when all siblings finish, marks the parent and syncs status to `project_manager`. |
| `stop.py`                       | `Stop`               | Blocks session end until every required phase is complete, tests passed, CI green (see `StopGuard`).                   |
| `async/user_prompt_submit.py`   | `UserPromptSubmit`   | Async. Invokes headless Claude to summarize `/build` instructions and resolves any `Pending...` rows in `violations.md`. |
| `async/task_completed.py`       | `TaskCompleted`      | Async. Runs `utils/auto_commit.py` to generate a commit message (headless Claude) and commit task output.              |

The dispatchers for `PreToolUse` and `TaskCreated` write `violations.md` (`lib/violations.py`) on every block for later audit.

## Guardrails (`guardrails/`)

Each guard is a class exposing `validate() → ("allow" | "block", message)`. `guardrails/__init__.py` wires them into `TOOL_GUARDS` (used by `PreToolUse`) and `STOP_GUARDS` (used by `SubagentStop`).

| Guard                      | Invoked on                           | What it checks                                                                                                                                                         |
| -------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PhaseGuard`               | `Skill` (PreToolUse)                 | Phase transition follows the workflow ordering. Handles `/continue`, `/plan-approved`, `/revise-plan`, `/reset-plan-review`. Skips auto-phases. Allows parallel `explore`+`research`. |
| `CommandGuard`             | `Bash` (PreToolUse)                  | Command is read-only, or matches the phase whitelist in `constants.COMMANDS_MAP`. Requires `--json` on `gh pr create` / `gh pr checks`.                                |
| `FileWriteGuard`           | `Write` (PreToolUse)                 | Phase permits writes; path matches the phase's target (`plan_file`, plan-declared code files, test patterns, report path). Plan writes must include the required sections and use bullet format for `Dependencies`/`Tasks`. |
| `FileEditGuard`            | `Edit` (PreToolUse)                  | Phase permits edits; file is plan/test/code in the current session. Edits to the plan must preserve required sections.                                                  |
| `AgentGuard`               | `Agent` (PreToolUse)                 | Agent type matches the phase's required agent, under `agent_count`. In review phases, blocks re-invocation until revisions (plan/tests/code) are done.                  |
| `WebFetchGuard`            | `WebFetch` (PreToolUse)              | URL host is in `config.safe_domains`.                                                                                                                                   |
| `TaskCreateToolGuard`      | `TaskCreate` (PreToolUse)            | Implement workflow: requires `metadata.parent_task_id` + `parent_task_title` matching a known project task.                                                             |
| `TaskCreatedGuard`         | `TaskCreated`                        | Build: task subject matches a plan bullet in `state.tasks`. Implement: subject matches a project task title; records child under parent.                                |
| `AgentReportGuard`         | `SubagentStop` (review/specs phases) | Validates that plan/code reviews have scores (1–100), tests/QA reports have a `Pass`/`Fail` verdict, and review reports list files to revise. Architect/backlog reports are structure-validated then auto-written to disk. |
| `StopGuard`                | `Stop`                               | All non-skipped phases completed, tests executed with `Pass` verdict, CI status `passed`. Skips test/CI checks in test mode.                                            |

## Recorder (`utils/recorder.py`)

Called by `post_tool_use.py` after a guard allows a tool. Dispatches on `tool_name`:

- **Skill** — records a phase transition (except for no-op skills `continue`, `revise-plan`, `plan-approved`, `reset-plan-review`). Handles the explore↔research parallel case.
- **Write** — marks plan/contracts/test/code/report files written, tracks specs docs, injects frontmatter metadata into the plan, and auto-extracts `## Dependencies`, `## Tasks`, `## Files to Create/Modify`, and contract names from the written markdown.
- **Edit** — records plan revision, test-file revision, code/test revisions.
- **Bash** — detects test execution (`TEST_RUN_PATTERNS`), PR creation (parses `gh pr create --json`), and CI status (parses `gh pr checks --json`).

Score/verdict/revision-file recorders are owned by `AgentReportGuard` but delegate to the same `Recorder`.

## Resolver (`utils/resolver.py`)

After every record, `Resolver.resolve()` runs two maps on the current phase:

- `_PHASE_RESOLVER_MAP` — review phases, agent phases, specs doc phases.
- `_TOOL_RESOLVER_MAP` — file-write phases (`plan`, `write-tests`, `write-code`, `write-report`) and delivery phases (`pr-create`, `ci-check`).

Score-based reviews compare against `config.score_thresholds` (plan/tests `confidence_score ≥ 80 & quality ≥ 80`; code `confidence_score ≥ 90 & quality ≥ 80`). Below threshold → review `Fail`. Three failed reviews → "exhausted," unlocking `/plan-approved` override. Verdict-based reviews (test-review, quality-check/validate) check for a `Pass` string.

After resolution, `auto_start_next()` advances through any `auto: true` phases, skipping TDD phases (`write-tests`, `test-review`, `tests-review`) when `--tdd` wasn't passed. `_check_workflow_complete()` sets `workflow_active=false` once every non-skipped phase is completed.

A checkpoint on `plan-review` is honored: the resolver refuses to advance until `/plan-approved` is invoked (or review is exhausted), matching the `Hook.discontinue(...)` emitted by `subagent_stop.py`.

## State (`lib/state_store.py`, `state.jsonl`)

`StateStore` is session-scoped. Each line in `state.jsonl` is a complete state snapshot for one `session_id`; reads and writes filter by that id and use `filelock` to serialize concurrent hooks. Operations: `load`, `save`, `update(fn)`, `get/set`, and dozens of domain helpers (`add_phase`, `set_phase_completed`, `add_plan_review`, `add_subtask`, …).

Schema lives in `models/state.py` as Pydantic models: `State`, `PhaseEntry`, `Agent`, `Plan`, `PlanReview`, `Tests`, `CodeFiles`, `CodeReview`, `PR`, `CI`. `utils/initializer.py` builds the initial state for `build`, `implement`, or `specs` from CLI args (`--tdd`, `--test`, `--skip-clarify`, `--skip-*`, story id, free-form instructions) and handles duplicate-story guard, `--reset`, and `--takeover`. For build workflows, the initializer also runs the headless-Claude clarity review (unless `--skip-clarify`) and seeds the `clarify` auto-phase as either `skipped` (verdict=clear) or `in_progress` with the captured `headless_session_id` (verdict=vague).

## Config (`config/config.json`)

Single source of truth, loaded by `config/config.py`. Declares:

- **`phases`** — array of phase objects. Each may carry `workflows`, capability flags, `agent`, `agent_count`, `auto`, `checkpoint`.
- **`plan_templates`** — required sections and bullet sections per workflow type.
- **`score_thresholds`** — plan / tests / code confidence & quality thresholds.
- **`safe_domains`** — whitelist for `WebFetchGuard`.
- **`paths`** — `state_jsonl`, plan/tests/code/report paths, specs doc paths, archive directories, log files, `clarity_review_prompt_file`.
- **`clarify.max_iterations`** — safety ceiling on `AskUserQuestion` rounds during the clarify auto-phase; default 10.
- **`specs_phases.max_report_retries`** — how many times the SubagentStop retry loop rejects an agent report before giving up. Defaults to 3. `config.specs_max_report_retries` is the accessor.

Specs validation schemas are **not** stored here. They are derived at runtime from the canonical template markdown files in `../templates/` via `utils/template_schema.TemplateSchema`, so editing a template is the only change needed to adjust the contract.

The `Config` class never hard-codes phase lists; they are derived from flags (`code_write_phases`, `read_only_phases`, `checkpoint_phase`, etc.).

## Constants (`constants/`)

The `constants/` package now spans several modules so each kind of constant lives next to its peers:

| File              | Contents                                                                                              |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| `constants.py`    | Tool/command whitelists, regex patterns, file/extension lists (everything that was here before).      |
| `phases.py`       | `REVIEW_PHASES` — the single set of phases where SubagentStop validates an agent report.              |
| `markers.py`      | `SPECIFICATIONS_MARKER` (`"## Specifications"`) and other markdown marker strings.                    |
| `paths.py`        | `COMMIT_BATCH_PATH`, `E2E_TEST_REPORT`, `STALE_THRESHOLD_MINUTES` — filesystem path constants.        |

### `constants/constants.py`

Regex patterns (`TEST_RUN_PATTERNS`, `SCORE_PATTERNS`, `STORY_ID_PATTERN`, `TABLE_PATTERN`), command lists (`READ_ONLY_COMMANDS`, `TEST_COMMANDS`, `PR_COMMANDS`, `CI_COMMANDS`), the `COMMANDS_MAP` phase→whitelist, `TEST_FILE_PATTERNS`, and `CODE_EXTENSIONS`.

Specs grammar (shared by `utils/validator.py` — these are invariants of the markdown grammar, not per-project policy): `SPECS_FIELD_MARKERS`, `SPECS_ID_REGEX_TEMPLATE`, `SPECS_BLOCKQUOTE_PATTERNS`, `SPECS_AC_MARKERS`, `SPECS_PLACEHOLDER_PREFIXES`, `SPECS_STORIES_HEADING`.

## Library (`lib/`)

| Module           | Role                                                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| `hook.py`        | `Hook` — stdin reader and stdout emitters (`block`, `advanced_block`, `system_message`, `discontinue`, `send_context`). |
| `state_store.py` | Session-scoped JSONL state with filelock (see above).                                                                   |
| `extractors.py`  | Pure parsers: skill name, agent name, scores, verdicts, markdown sections/tables/bullets, plan sections, contract names, build instructions. |
| `parser.py`      | CLI-arg parsers for `initializer.py` and frontmatter reader.                                                            |
| `archiver.py`    | Moves `latest-plan.md` to `archive/` at workflow start.                                                                  |
| `clarity_check.py` | Headless-Claude wrapper used by the build initializer + post_tool_use hook to evaluate prompt clarity (`run_initial`, `run_resume`). |
| `injector.py`    | Writes YAML frontmatter (session_id, workflow_type, story_id, date) into the plan after `Write`.                        |
| `file_manager.py`| Locked JSON/JSONL helpers used by GitHub-project and tests. Also backs the `auto_commit` ledger.                        |
| `violations.py`  | Append-only markdown log of every block (`logs/violations.md`). Fills in prompt summaries async.                        |
| `paths.py`       | Pure path helpers (`basenames`, `path_matches`) shared by guards, recorder, and resolver.                                |
| `shell.py`       | `run_git()`, `invoke_claude()`, and `invoke_codex()` subprocess wrappers; one place to mock for tests.                   |
| `scoring.py`     | `scores_valid()` and `verdict_valid()` — pure validators reused by `AgentReportGuard` and `Recorder`.                    |
| `parallel_check.py` | `is_parallel_explore_research()` predicate shared by the recorder, resolver, and guard.                              |
| `specs_validation.py` | `validate_architecture_content` / `validate_backlog_content` — pure validators used by `AgentReportGuard`.          |

### Violation `Phase` column — how it's derived

`pre_tool_use.resolve_violation_phase()` picks the label for the `Phase` column:

1. If the user was in an active phase at the time of the block → use that phase (most accurate for audit/log consumers).
2. If no phase is active **and** the blocked tool is `Skill` → use the attempted skill name (invoking a skill is what enters a phase, so its name is the most meaningful label).
3. Otherwise → use the sentinel `pre-workflow`. We deliberately do **not** fall back to the first workflow phase (e.g. `vision`) because that would misleadingly imply the user had entered that phase when they hadn't.

## Utilities (`utils/`)

| Module                | Role                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `initializer.py`      | Called from skill frontmatter bash to build initial state and archive prior plan/contracts.                    |
| `recorder.py`         | Records state after allowed tool uses (see above).                                                             |
| `resolver.py`         | Evaluates state and advances phases (see above).                                                               |
| `validator.py`        | `SpecsValidator` — validates architecture / constitution / product-vision / backlog (md+json) and converts backlog markdown to JSON. Schemas come from `utils/template_schema.TemplateSchema` (parsed directly from `../templates/*.md`); grammar constants live in `constants.SPECS_*`. |
| `template_schema.py`  | `TemplateSchema` — parses a spec template markdown file into a structural schema (metadata fields, enums, required sections/subsections/tables, backlog priorities + item types). The template file is the single source of truth; `SpecsValidator` caches one schema per doc type. |
| `specs_writer.py`     | Thin wrapper over `SpecsValidator` that writes validated architect/backlog agent reports to `projects/docs/`. |
| `auto_commit.py`      | Async. Claims dirty files per task-batch via `commit_batch.json`, invokes headless Claude for a message, commits. Ledger I/O routes through `lib/file_manager.py`; subprocess via `lib/shell.py`. |
| `summarize_prompt.py` | Async. Summarizes `/build` instructions via headless Claude (`lib/shell.invoke_claude`) and writes `prompt_summary` to state.              |

## Specs templates (`../templates/`)

Plain markdown + sample JSON consumed by the specs workflow commands. All specs artifacts live in one flat directory — previously split across `skills/*/templates/`, now consolidated here.

| File                       | Consumer                                   |
| -------------------------- | ------------------------------------------ |
| `architecture.md`          | `commands/architect.md`, `commands/specs.md` |
| `constitution.md`          | `commands/specs.md`                        |
| `product-vision.md`        | `commands/vision.md`, `commands/test-specs.md`, `commands/specs.md` |
| `backlog.md`               | `commands/backlog.md`, `commands/specs.md` |
| `backlog-sample.json`      | reference schema for `SpecsValidator.validate_backlog_json` |
| `visionize-questions.md`   | `commands/vision.md` discovery questions   |
| `plan.md`                  | build workflow plan template                |
| `implement-plan.md`        | implement workflow plan template            |
| `clarity-review.md`        | `lib/clarity_check.py` (headless-Claude prompt) |

## Adjacent packages

- **`../project_manager/`** — local-first project manager (`cli.py` → `ProjectManager`) backed by `issues/{stories,backlog,metadata}.json`. Used by the implement workflow to load project tasks, record child subtasks, and mark tasks `Done` on completion. CLI subcommands: `list`, `view`, `summary`, `progress`, `update`, `add-task`, `add-story`, `sync`, `unblocked`.
- **`headless_claude/claude.py`** — thin wrapper around `subprocess.run(["claude", "-p", …])` used by the async dispatchers to generate summaries and commit messages without blocking the live session.
- **`headless/codex/`** — headless-Codex helpers that delegate the subprocess call to `lib/shell.invoke_codex()`. `codex_plan_review.py` loads the prompt template from `headless/prompts/codex/plan_review.md`, substitutes the build-phase plan body, and asks Codex to return a scored plan-review report (Confidence + Quality + `Pass`/`Fail`) matching `AgentReportGuard`'s plan-review format. Fail-open: returns `None` if the plan file or `codex` binary is missing.
- **`headless/claude/`** — headless-Claude counterpart that delegates to `lib/shell.invoke_claude()`. `claude_plan_review.py` uses the same orchestration as the Codex version but loads its prompt from `headless/prompts/claude/plan_review.md`, letting the build phase fan out a second plan-review opinion without coupling to Codex. Fail-open on missing plan/binary.
- **`tests/`** — pytest suite covering dispatchers, guardrails, recorder, resolver, extractors, state store, initializer, auto-commit, specs flow, task lifecycle, and more.

## Data flow summary

```
PreToolUse          stdin → TOOL_GUARDS[tool_name].validate()
                    block → permissionDecision:"deny" + log_violation
                    allow → systemMessage(reason)

PostToolUse         Recorder.record(hook_input, config)
                    resolve(config, state)            # auto-complete phase, auto-start next

PostToolUseFailure  Bash only: record_test_execution → resolve

SubagentStart       state.add_agent(Agent(name, "in_progress", agent_id))

SubagentStop        state.update_agent_status(agent_id, "completed") → resolve
                    review/specs phase → AgentReportGuard.validate()
                    plan-review passed → Hook.discontinue("Plan approved.")

TaskCreated         TaskCreatedGuard.validate()
                    build → subject must match a plan ## Tasks bullet
                    implement → subject must match a project task; record child

TaskCompleted       sync: mark child + possibly parent completed
                    async: auto_commit (headless Claude + git commit)

UserPromptSubmit    async: summarize_prompt (headless Claude)

Stop                StopGuard.validate()
                    missing phases/tests/CI → decision:"block" with reasons
```

## Phase lifecycle highlights

- **Checkpoint** — `plan-review` completion emits `{continue:false, stopReason:"Plan approved. Review the plan before proceeding."}` so the user confirms before automation continues. `/plan-approved` bypasses the checkpoint.
- **Specs SubagentStop retry cap** — For architect/backlog (and the other review phases), invalid agent output triggers the SubagentStop block (`exit 2`), which is Claude Code's native "subagent, try again" signal. The stderr includes the template path and list of validation errors so the agent can course-correct. After `specs_phases.max_report_retries` (default 3) rejections on the same `agent_id`, the dispatcher marks the agent `status="failed"`, logs a single violation, and releases the subagent cleanly (`exit 0`) so the workflow halts for operator intervention instead of looping forever. `agents[].status == "failed"` is excluded from `count_agents`, so an operator or a `/continue` can immediately retry with a fresh Architect / ProductOwner agent.
- **Sub-phases / revisions** — failed reviews (`plan-review`, `test-review`/`tests-review`, `code-review`) keep the phase `in_progress`; the next agent invocation is blocked until the revision files listed by the reviewer have been edited. After 3 failures the review is "exhausted" and `/plan-approved` is allowed.
- **TDD toggle** — `--tdd` on `/build` or `/implement` opts into `write-tests` and `test-review`/`tests-review`; without it, those phases are skipped in both the resolver and `StopGuard`.
- **Test mode** — `--test` bypasses live-test / CI checks in `StopGuard`, allows writes to `state.jsonl` and `.claude/reports/E2E_TEST_REPORT.md`, and unlocks `/reset-plan-review`.
- **Parallel explore+research** — while `explore` is `in_progress`, `Research` agents and the `research` skill are allowed; recorder tracks the parallel transition.

## State file

Default: `scripts/state.jsonl`. One JSON object per line per session. Lock file: `scripts/state.lock`. Violations: `logs/violations.md` + `logs/violations.lock`.

### Environment overrides (tests)

| Variable                     | Overrides                                     |
| ---------------------------- | --------------------------------------------- |
| `TASK_CREATED_STATE_PATH`    | state path used by `task_created.py`          |
| `SUBAGENT_STOP_STATE_PATH`   | state path used by `subagent_stop.py`         |
| `VIOLATIONS_PATH`            | target file for `lib/violations.log_violation`|

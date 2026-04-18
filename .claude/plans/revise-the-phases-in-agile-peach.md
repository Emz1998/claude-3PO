# Revise Build Workflow Phases

## Context

The `build` workflow carries two phases (`install-deps`, `define-contracts`) that add ceremony without enough payoff, and it lacks two gates that would improve quality:

- **Upfront clarity**: ambiguous prompts cost agent time. A headless-Claude review on `UserPromptSubmit` can detect vague prompts. A persistent headless session (resumed via `headless_session_id`) re-evaluates after every `AskUserQuestion` answer, so the model builds context conversationally rather than being re-briefed each time. The `clarify` phase is an **auto-phase** — no skill to invoke; it activates automatically when the initial headless verdict is `vague` and completes automatically once a resumed verdict is `clear`.
- **Explicit technical decisions**: research findings should be followed by recorded decisions before planning. The `specs` workflow already has this; extend it to `build`.

**Outcome**: leaner, requirement-first build workflow. Install/contracts ceremony is deleted outright (no backward compat). A new `/clarify` phase is driven by a persistent headless-Claude session that evaluates clarity after each Q&A round. A new `/decision` phase shares the existing specs resolver and doc.

## New Build Phase Order

1. `clarify` *(new, **auto-phase** — runs only if headless-Claude review returns "vague"; no skill)*
2. `/explore` *(parallel with research)*
3. `/research` *(parallel with explore)*
4. `/decision` *(new for build — shared with specs)*
5. `/plan`
6. `/plan-review`
7. `create-tasks` *(auto)*
8. `write-tests` *(auto, TDD only)*
9. `/test-review` *(TDD only)*
10. `write-code` *(auto)*
11. `/quality-check`
12. `/code-review`
13. `/pr-create`
14. `/ci-check`
15. `/write-report`

Removed: `install-deps`, `define-contracts`.

## Removal Policy — No Backward Compatibility

All code, config, tests, fixtures, docs, state fields, and paths for `install-deps` and `define-contracts` are **deleted outright**: no deprecation shims, no `workflows: []` parking, no legacy fallbacks, no commented-out code, no state-key compat. `contracts_file` and `contracts_archive_dir` config paths are removed. State fields `state.dependencies` and `state.contracts` and all setters/getters are removed. Recorder methods, guardrail branches, resolver methods, tool-resolver entries, tests, templates, and prompt references are all fully excised. Final repo-wide grep must return zero hits on the dead tokens.

## Clarity-Check Mechanism (`/clarify` + Resumable Headless Session)

### Key idea

One persistent headless-Claude session per user prompt. Its `headless_session_id` is captured on the first run and **resumed** after every `AskUserQuestion` answer. Claude therefore accumulates context conversationally instead of being re-briefed with a growing Q&A transcript each call.

### Trigger flow

1. User runs `/build <prompt>`.
2. `build.md` already calls `initializer.py` via its `!` bash line (line 15). **Extend `initializer.py`** so that — for the `build` workflow and when `--skip-clarify` is not in `$ARGUMENTS` — it runs the headless check inline:
   - Run headless Claude: `claude -p <REVIEW_PROMPT>` with the user's prompt as input. The review prompt instructs Claude to reply with exactly one token: `clear` or `vague`.
   - Capture the new session's `headless_session_id` (via `claude --print --output-format json`, which emits it in stdout).
   - Parse the verdict.
3. If verdict is `clear`: initializer writes `clarify` to `state.phases` with `status: "skipped"`; workflow proceeds to `/explore`.
4. If verdict is `vague`: initializer writes `clarify` with `status: "in_progress"`, `headless_session_id: <captured>`, `iteration_count: 0`. The phase guardrail then blocks all non-clarify tools until the phase resolves.

**No new hook needed.** Keeping the logic in the initializer means it runs synchronously as part of workflow bootstrap — identical pattern to the rest of `build`'s initialization.

### Auto-phase behavior (no skill)

- `clarify` is defined with `"auto": true` in `config.json`. The agent does **not** invoke a `/clarify` skill.
- `build.md` instructs the agent: "when the current phase is `clarify`, call `AskUserQuestion` to resolve the ambiguity in the user's original prompt — no other tools until the phase clears."
- The agent calls `AskUserQuestion` as many times as needed (up to 4 questions per call; no per-cycle limit other than the safety ceiling).
- After **each** `AskUserQuestion` completes (user has answered), a **`PostToolUse` hook** fires on the `AskUserQuestion` tool:
  - Read `headless_session_id` from the in-progress `clarify` phase in `state`.
  - Resume the session: `claude -p --resume <headless_session_id> <latest Q&A payload>` — the payload is just the current question/answer pair (the resumed session already has all prior history).
  - Parse the verdict.
  - Update the phase: `iteration_count += 1`.
- If verdict is `clear`: mark the phase `completed`; `auto_start_next` advances to `/explore`.
- If verdict is `vague`: phase stays `in_progress`; the agent issues the next `AskUserQuestion`. Repeat.

### Safety ceiling

- Configurable `clarify.max_iterations` (default **10**). Compared directly to `iteration_count` on the phase object.
- Enforced by `PhaseGuard` on `AskUserQuestion` tool use: once `iteration_count >= max_iterations`, further `AskUserQuestion` calls are blocked with a user-facing error ("Max clarify iterations reached — please simplify the prompt and re-run `/build`"). The phase does **not** auto-advance; the user must intervene.

### `--skip-clarify` flag

- `/build --skip-clarify <prompt>`: the hook skips the headless check entirely. State marks `clarify` phase `skipped`. Use when the user is confident the prompt is unambiguous.

## State — Clarify Phase Fields (inside `state.phases`)

Only two fields are persisted, attached directly to the `clarify` phase object inside the existing `state.phases` list. **No new JSONL record types. No Q&A transcript.** The resumed headless session already has the conversation history — we just need to know which session to resume and how many times we've iterated.

```json
{
  "name": "clarify",
  "status": "in_progress",
  "headless_session_id": "sess_ab12cd34",
  "iteration_count": 3
}
```

- `headless_session_id`: captured on the initial headless run during `UserPromptSubmit`; **reused verbatim** on every resume. Single session per user prompt.
- `iteration_count`: starts at `0` (initial check only). Increments by `1` on each `PostToolUse` resume triggered by an `AskUserQuestion` answer. Guardrail blocks further AskUserQuestion once it reaches `clarify.max_iterations`.

### Verdict handling

The current verdict is not persisted — it's consumed inline by the hook:
- `clear` on initial check → mark phase `skipped`, proceed to `explore`.
- `vague` on initial check → set phase to `in_progress` with `headless_session_id` and `iteration_count: 0`.
- `clear` on resume → mark phase `completed`, proceed to `explore`.
- `vague` on resume → increment `iteration_count`, phase stays `in_progress`.

## Changes by File

### 1. Config — `claude-3PO/scripts/config/config.json`
- **Delete** `install-deps` and `define-contracts` phase entries (lines 38–39).
- **Delete** path entries `contracts_file` (line 201) and `contracts_archive_dir` (line 202). No replacement.
- Add `clarify` entry: `{"name": "clarify", "workflows": ["build"], "read_only": true, "auto": true}`, ordered before `explore`.
- Extend the `decision` entry's `workflows` from `["specs"]` to `["specs", "build"]`.
- Add `paths.clarity_review_prompt_file`: `"templates/clarity-review.md"`.
- Add config block `"clarify": { "max_iterations": 10 }`.

### 2. Build command — `claude-3PO/commands/build.md`
- **Delete** `### 5. /install-deps` (lines 82–89) and `### 6. /define-contracts` (lines 91–98) sections.
- **Delete** references to `.claude/contracts/latest-contracts.md` in the `/plan` section (line 61) and References section (line 180). Remove the contract-writing step from `/plan`.
- Renumber phases 1–15.
- Add new `### 1. clarify (AUTO)` section: describe the auto-phase mechanics, the headless-session trigger, the resume-on-AskUserQuestion loop, the `max_iterations` cap, and the `--skip-clarify` flag. Mirror the wording used for existing auto-phases (`write-tests (AUTO)`, `write-code (AUTO)`) — "starts automatically — do NOT invoke as a skill."
- Add new `### 4. /decision` section after `/research`.
- Update `argument-hint` to include `[--skip-clarify]`.

### 3. Command files — `claude-3PO/commands/`
- **Delete**: `install-deps.md`, `define-contracts.md`.
- **Do NOT create** a `clarify.md` skill. `clarify` is an auto-phase, no skill entry point. All agent guidance lives inside `build.md` alongside the other auto-phase descriptions (write-tests, write-code).
- **Update**: `decision.md` — generalize for both workflows (drop "Phase 3" specs-specific framing; keep the 10-question structure; continue writing `projects/docs/decisions.md`).

### 4. Initializer — headless kickoff (no new hook)
- File: existing `claude-3PO/scripts/utils/initializer.py` (already invoked by `build.md` via `!`).
- Add a new module `claude-3PO/scripts/lib/clarity_check.py` (single responsibility: headless review).
  - `run_initial(prompt: str) -> (headless_session_id, verdict)` — shells out to `claude -p --output-format json`, parses `headless_session_id` and verdict, returns both.
  - `run_resume(headless_session_id: str, qa_payload: str) -> verdict` — shells out to `claude -p --resume <headless_session_id> --output-format json` with the latest Q&A.
- Initializer logic: when the workflow arg is `build` and `--skip-clarify` is not in `$ARGUMENTS`, call `clarity_check.run_initial(user_prompt)`. If `verdict == "clear"`, add `clarify` to `state.phases` with `status: "skipped"` and no other fields; `auto_start_next` picks `explore`. If `verdict == "vague"`, add `clarify` with `status: "in_progress"`, `headless_session_id`, `iteration_count: 0`.
- Keep the initializer function single-responsibility per `CLAUDE.md` style rules (max 15 lines): the clarity step is its own helper called from the main init flow.
- **No new dispatcher/hook file**. `UserPromptSubmit` is not modified.

### 5. PostToolUse hook — AskUserQuestion resume
- File: existing `claude-3PO/scripts/dispatchers/post_tool_use.py`.
- Add a handler: when `tool_name == "AskUserQuestion"` and current phase is `clarify`:
  - Read `headless_session_id` from the in-progress `clarify` phase in `state`.
  - Build a Q&A payload from the tool input (questions) and tool response (user answers).
  - Call `clarity_check.run_resume(headless_session_id, qa_payload)`.
  - Increment `iteration_count` on the phase.
  - If verdict is `clear`, mark the phase `completed` (`state.set_phase_completed("clarify")`).

### 6. Resolver — `claude-3PO/scripts/utils/resolver.py`
- **Delete** `_resolve_install_deps` (~lines 384–391), `_resolve_define_contracts` (~lines 454–465), helpers `_find_contract_names_in_files`, `_are_contracts_written`, `_are_contracts_validated`, `_validate_and_complete_contracts` (~lines 393–452).
- **Delete** `"install-deps"` and `"define-contracts"` entries from `_TOOL_RESOLVER_MAP` (lines 697–698).
- **Delete** the `# ── Install / contracts ──` section comment (~line 382).
- **No new resolver needed** for `clarify`. The phase's status is flipped directly to `completed` or `skipped` by the `UserPromptSubmit` dispatcher or the `PostToolUse` handler — there is no secondary completion signal to poll. Skip registering in `_PHASE_RESOLVER_MAP`. `auto_start_next` handles advancing to `explore` once status is `completed`/`skipped`.
- `_resolve_decision`: no change — works unchanged for build.

### 7. Recorder / State writer — `claude-3PO/scripts/utils/recorder.py`
- **Delete** `record_deps_installed` and every contract-related recording method / branch / path mapping (~lines 187–230, 696–719). Remove imports and helpers that become dead code.
- Add phase-mutation helpers on the state writer (not new JSONL record types): `set_clarify_session(headless_session_id)`, `bump_clarify_iteration()`. They update fields on the `clarify` phase dict inside `state.phases`.
- Reuse the existing `set_phase_completed(name)` / `set_phase_skipped(name)` paths for transitions.

### 8. Guardrails — `claude-3PO/scripts/guardrails/`
- `write_guard.py`: **delete** every `install-deps`/`define-contracts` branch (~lines 58–59, 345–357, 363–370, 498–501). Delete now-dead helpers.
- `phase_guard.py`:
  - Verify parallel explore+research special case (~lines 440–444) still works with `clarify` inserted before `explore`. Expected: unchanged — clarify resolves → explore starts → research parallel with explore.
  - `clarify` phase: only `AskUserQuestion`, `Read`, `Glob`, `Grep` tools permitted. All writes blocked.
  - Enforce `clarify.max_iterations`: read `iteration_count` directly off the in-progress `clarify` phase; block further `AskUserQuestion` once it reaches the cap, with a user-facing error.
- Grep `guardrails/` for `install-deps`, `define-contracts`, `contracts`, `dependencies` — delete remaining refs.

### 9. State module
- **Delete** `state.dependencies`, `state.contracts`, and all their setters/getters.
- Allow the `clarify` phase dict in `state.phases` to carry two extra keys: `headless_session_id: str` and `iteration_count: int`. No schema migration — these keys simply don't exist for other phases or when `clarify` is skipped.
- Add accessor `state.get_clarify_phase() -> dict | None` for the dispatcher and guard to read/update the fields cleanly.

### 10. Templates — `claude-3PO/templates/`
- **Create** `clarity-review.md` — the review prompt sent to headless Claude. Instructs Claude to reply with **exactly one token**: `clear` or `vague`. Includes placeholders for the user prompt.

### 11. Tests — `claude-3PO/scripts/tests/`
- **Delete**: `test_define_contracts.py`; any install-deps-specific file if present.
- **Update**: `test_config.py`, `test_validators.py`, `test_revise_plan.py`, `test_pre_tool_violation_phase.py`, `test_auto_transition.py` — strip install-deps/define-contracts fixtures and assertions; add clarify + decision-in-build coverage.
- **Create**:
  - `test_clarity_check.py` — mocks `subprocess.run` for headless Claude; covers initial-run `headless_session_id` capture, resume calls, `clear`/`vague`/parse-error paths.
  - `test_clarify_phase.py` — covers: auto-skip on first-pass clear (phase marked `skipped`); resume-on-AskUserQuestion loop increments `iteration_count`; progression to `/explore` on `clear`; `--skip-clarify` behavior; `max_iterations` ceiling blocks `AskUserQuestion`.
  - `test_decision_build_phase.py` — `decision` is active in build workflow, writes to shared `projects/docs/decisions.md`.
- Grep `scripts/tests/` for dead tokens after edits — zero hits.
- Per CLAUDE.md: write/revise tests **first**, then implement.

### 12. Docs — READMEs, templates, prompts under `claude-3PO/`
- Delete any README/template/prompt that mentions `install-deps`, `define-contracts`, `contracts.md`. Rewrite affected sections for the new phase order; no strikethroughs, no "previously known as" notes.

### 13. Final sweep
- Repo-wide grep: `grep -rE "install[-_]deps|define[-_]contracts|latest-contracts|state\.(dependencies|contracts)|record_deps_installed|contracts_file|contracts_archive_dir" claude-3PO/` → **zero** hits outside `claude-3PO/logs/`.
- Delete any now-empty directories (`.claude/contracts/` if present).

## Reused Patterns

- `_resolve_decision` (resolver.py, line 690) — existing resolver, reused as-is for build once `workflows` array is extended.
- `commands/decision.md` — existing specs command, generalized.
- `_resolve_doc_phase` helper — already used by `vision`/`decision`.
- `--skip-explore` / `--skip-research` CLI convention — apply to `--skip-clarify`.
- Existing auto-phase pattern (`write-tests`, `write-code`, `create-tasks` in config.json with `"auto": true`) — apply the same flag to `clarify`. Reuse `auto_start_next` in resolver.py for start and completion transitions.
- Existing `initializer.py` (already called by `build.md` via `!`) — hook the initial clarity check into this file instead of adding a new dispatcher.
- Existing `post_tool_use.py` dispatcher — hook the resume-on-AskUserQuestion logic into this file.
- Existing phase-mutation pattern in `recorder.py` / state writer (`set_phase_completed`, `set_phase_skipped`) — extend with `set_clarify_session` / `bump_clarify_iteration`. No new JSONL record types.

## Verification

1. Unit tests: `pytest claude-3PO/scripts/tests/` — all updated/new tests pass.
2. Config sanity: `python3 -c "from scripts.config.config import Config; c = Config(); print([p['name'] for p in c.build_phases])"` — prints the new 15 phases starting with `clarify`.
3. E2E — **ambiguous prompt**: run `/build "do the thing"`. Confirm: `clarify` phase appears in `state.phases` with `status: "in_progress"`, a captured `headless_session_id`, and `iteration_count: 0`; AskUserQuestion fires; PostToolUse increments `iteration_count` each round; phase flips to `completed` when headless returns `clear`; workflow advances to `/explore`.
4. E2E — **clear prompt**: run `/build "add a /logout endpoint to src/api/auth.py that invalidates the session cookie"`. Confirm `clarify` appears in `state.phases` with `status: "skipped"`, no `headless_session_id` or `iteration_count`; workflow jumps to `/explore`.
5. E2E — **skip flag**: `/build --skip-clarify "anything"` → no headless call; `clarify` marked `skipped`.
6. E2E — **iteration ceiling**: mock headless responses to stay `vague` and confirm the guardrail blocks AskUserQuestion after `max_iterations` with the user-facing error.
7. Phase-guard check: attempt `/decision` before `/research` → blocked.
8. Dead-token grep returns zero hits outside `claude-3PO/logs/`.

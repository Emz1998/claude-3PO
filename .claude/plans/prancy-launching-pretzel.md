# Plan: `/specs` Workflow

## Context

Replace standalone `backlog/`, `architect/`, and `visionize/` skill directories with flat commands under `commands/`. A new `/specs` command orchestrates a 5-phase pipeline producing project docs. Agent outputs validated by extending `AgentReportGuard` to handle specs phases at `SubagentStop`.

## Phases

```
/vision → /strategy → /decision → /architect → /backlog
```

| Phase | Command | Who | Output |
|---|---|---|---|
| `vision` | `/vision` | Main agent | `product-vision.md` |
| `strategy` | `/strategy` | 3 Research agents (parallel) | Context for decisions |
| `decision` | `/decision` | Main agent | `decisions.md` |
| `architect` | `/architect` | Architect agent | `architecture.md` (validated + auto-written) |
| `backlog` | `/backlog` | ProductOwner agent | `backlog.md` + `backlog.json` (validated + auto-written) |

All output to `projects/docs/` from cwd.

## Vision Questions (10)

Asked via AskUserQuestion during `/vision` phase:

1. What is the name of your project and who is building it?
2. Who are your target users and what problem do they face today?
3. What has changed recently that makes now the right time to solve this problem?
4. In one paragraph, what does your product do and how does it work at a high level?
5. What are your top 3 value propositions and the user benefit of each?
6. Who are your main competitors or alternatives, and what is your advantage over them?
7. What features are in your MVP and what is explicitly excluded?
8. What is your revenue model and what key metrics will you track?
9. Who is on your team and what is your current runway or budget?
10. What does success look like at MVP launch, 6 months, and 12 months?

## Strategy — 3 Research Agents (parallel)

Each agent reads `product-vision.md` first, then focuses on its area:

1. **Agent 1 — Tech stack & infrastructure**: Research best-fit languages, frameworks, databases, and hosting for the product's requirements. Evaluate trade-offs (cost, scalability, team expertise).
2. **Agent 2 — Architecture patterns & integrations**: Research architecture styles (monolith vs microservices, event-driven, serverless), API design patterns, and third-party integrations needed.
3. **Agent 3 — Security, compliance & DevOps**: Research authentication strategies, data privacy requirements, CI/CD pipeline options, and deployment strategies for the target platform.

## Decision Questions (10)

Asked via AskUserQuestion during `/decision` phase, informed by strategy research:

1. Which programming language and framework will you use for the backend?
2. Which frontend framework or platform will you build on?
3. Which database type and specific product will you use?
4. How will you handle authentication and authorization?
5. Will you start with a monolith, microservices, or serverless architecture?
6. Which cloud provider and hosting approach will you use?
7. What is your API strategy — REST, GraphQL, or RPC?
8. How will you handle CI/CD and deployment?
9. What third-party services or APIs will you integrate?
10. What are your non-negotiable technical constraints or requirements?

## State Schema (`specs` workflow)

```json
{
  "session_id": "abc-123",
  "workflow_active": true,
  "status": "in_progress",
  "workflow_type": "specs",
  "phases": [
    {"name": "vision", "status": "completed"},
    {"name": "strategy", "status": "in_progress"}
  ],
  "agents": [
    {"name": "Research", "status": "completed", "tool_use_id": "toolu_1"},
    {"name": "Research", "status": "in_progress", "tool_use_id": "toolu_2"}
  ],
  "skip": [],
  "instructions": "",
  "docs": {
    "product_vision": {"written": false, "path": ""},
    "decisions": {"written": false, "path": ""},
    "architecture": {"written": false, "path": ""},
    "backlog": {"written": false, "md_path": "", "json_path": ""}
  }
}
```

Fields reused from build/implement: `session_id`, `workflow_active`, `status`, `workflow_type`, `phases`, `agents`, `skip`, `instructions`.

Fields NOT needed (build/implement only): `tdd`, `story_id`, `plan`, `tests`, `code_files`, `quality_check_result`, `pr`, `ci`, `report_written`, `contracts`, `dependencies`, `tasks`, `created_tasks`, `project_tasks`, `code_files_to_write`, `prompt_summary`.

New field: `docs` — tracks which documents have been written and their paths.

## Config Changes (`config.json`)

### Phases (add to `phases` array)

```json
{"name": "vision", "workflows": ["specs"], "docs_write": true},
{"name": "strategy", "workflows": ["specs"], "read_only": true, "agent": "Research", "agent_count": 3},
{"name": "decision", "workflows": ["specs"], "docs_write": true},
{"name": "architect", "workflows": ["specs"], "read_only": true, "agent": "Architect", "agent_count": 1},
{"name": "backlog", "workflows": ["specs"], "read_only": true, "agent": "ProductOwner", "agent_count": 1}
```

Also migrate `agent_count` into existing phases and remove the top-level `agents` map:

```json
{"name": "explore", ..., "agent": "Explore", "agent_count": 3},
{"name": "research", ..., "agent": "Research", "agent_count": 2},
{"name": "plan", ..., "agent": "Plan", "agent_count": 1},
{"name": "plan-review", ..., "agent": "PlanReview", "agent_count": 3},
{"name": "test-review", ..., "agent": "TestReviewer", "agent_count": 3},
{"name": "tests-review", ..., "agent": "TestReviewer", "agent_count": 3},
{"name": "quality-check", ..., "agent": "QASpecialist", "agent_count": 3},
{"name": "validate", ..., "agent": "QASpecialist", "agent_count": 3},
{"name": "code-review", ..., "agent": "CodeReviewer", "agent_count": 3}
```

Delete the top-level `"agents": {...}` map. Update `Config.get_agent_max_count()` to read from phase entries instead.

### Paths (add to `paths` map)

```json
"product_vision_file": "projects/docs/product-vision.md",
"decisions_file": "projects/docs/decisions.md",
"architecture_file": "projects/docs/architecture.md",
"backlog_md_file": "projects/docs/backlog.md",
"backlog_json_file": "projects/docs/backlog.json"
```

## What to Create

1. **6 commands** — `specs.md`, `vision.md`, `strategy.md`, `decision.md`, `architect.md`, `backlog.md` under `commands/`
2. **`specs_writer.py`** — `scripts/utils/specs_writer.py` — writes md (and json for backlog) to disk
3. **`decision_questions.md`** — the 10 decision questions listed above

## What to Modify

4. **`initializer.py`** — `build_initial_state(workflow_type, ...)` already takes workflow_type. Add an early return for `"specs"` that returns the minimal `docs`-based schema. Skip archive/story-id/takeover logic when `workflow_type == "specs"`.
5. **`config.py`** — update `get_agent_max_count()` to read `agent_count` from phase entries instead of the top-level `agents` map. Remove `agents` property. Add path accessors for new specs paths.
5. **`agent_report_guard.py`** — extend to handle `architect` and `backlog` phases: validate `last_assistant_message` against templates, auto-write via `specs_writer`
6. **`subagent_stop.py`** — extend phase check to include `architect` and `backlog`
7. **`guardrails/__init__.py`** — no new guard needed (reuse `agent_report`)
8. **`config.json`** — add 5 specs phases, migrate agent counts into phases, add output paths
9. **`resolver.py`** — add 5 phase resolvers (check `docs.{key}.written`)
10. **`recorder.py`** — record vision/decision Write events to state
11. **`state_store.py`** — add `docs` accessors

## What to Delete

11. `skills/backlog/`, `skills/architect/` — replaced by commands + central guard
12. Keep `skills/visionize/` (questions, validators, templates imported by guard)

## Reuse

All validators/converters as-is: `validate_product_vision`, `validate_architecture`, `validate_backlog_md`, `validate_backlog_json`, `backlog_json_converter`. Extend `AgentReportGuard` rather than creating a new guard class.

## Code Style Rules

- **Function length**: 5-15 lines ideal, 15-20 acceptable if readable, never exceed 20
- Split large functions into focused helpers
- Each function does one thing

## Verification

- Unit tests for extended `AgentReportGuard`, `specs_writer`, resolver changes
- Regression: `python3 -m pytest claude-3PO/scripts/tests/ -v`
- E2E: pipe valid/invalid content to SubagentStop hook

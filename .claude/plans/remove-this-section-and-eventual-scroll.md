# Plan: Replace `specs_schemas` Config Block with Template-Driven Validation

## Context

`claude-3PO/scripts/config/config.json` lines 192–406 (`specs_schemas`) currently holds the full structural schema for the four specs documents (architecture, constitution, product_vision, backlog). The schema duplicates what the markdown templates in `claude-3PO/templates/` already express (sections, subsections, metadata fields, tables, enum legends), which means any template change requires a parallel config update or validation silently drifts.

**Goal:** Delete the `specs_schemas` block and make the template files the single source of truth. Validation works by parsing both the template and the agent report and diffing their structures.

**Outcome:** One place to edit (the template). No drift. The schema block (~215 lines of JSON) disappears from config.

---

## Approach

Introduce a `TemplateSchema` object produced by parsing a template markdown file, then compare a parsed report to that schema. `SpecsValidator` stops reading `config.specs_schemas(...)` and instead calls `TemplateSchema.from_file(templates_dir / f"{doc}.md")`.

### What the template already encodes (verified)

| Template | Metadata fields | Enums | Sections | Tables |
|---|---|---|---|---|
| `architecture.md` | bold `**Field:**` lines 5–11 | `**Status:** Draft / In Review / Approved` (line 9) → inline `/`-separated | `## 1.` … `## 13.` | `2.1 Architecture Style`, `2.2 ADRs`, `1.3 Definitions`, etc. |
| `constitution.md` | blockquote `> **Project:**` lines 3–6 | none | `#`-level sections | Tooling, DoD |
| `product-vision.md` | bold `**Field:**` lines 3–6 | none | `##` sections + `###` subs | Segment, Value Props, MVP Scope, Revenue, Metrics, Risks, Team |
| `backlog.md` | bold `**Field:**` lines 3–4 | Priority Legend bullets → `P0/P1/P2`; ID Conventions table → `US/TS/SK/BG` + `story_type_names` map | `## Priority Legend`, `## ID Conventions`, `## Stories` | ID Conventions |

All enum data exists in parseable form in the templates today — nothing needs to be synthesized.

### Pieces to build

1. **`claude-3PO/scripts/utils/template_schema.py`** — new module. `TemplateSchema` dataclass with fields `metadata_fields`, `status_enums` (dict field→allowed values), `required_sections` (ordered), `required_subsections` (parent→list), `required_tables` (section→first-row header), plus backlog-only `valid_priorities`, `valid_item_types`, `story_type_names`. Classmethod `from_markdown(text) -> TemplateSchema` composes small single-purpose parsers (each ≤15 lines per CLAUDE.md rule):
   - `_parse_metadata_block(text)` — bold `**Field:**` or blockquote `> **Field:**` lines before the first heading.
   - `_parse_status_enums(metadata_lines)` — any metadata value containing ` / ` splits into the enum list for that field.
   - `_parse_section_tree(text, level)` — `##`/`#` headings and `###`/`##` children, via the existing `lib.extractors.extract_md_sections`.
   - `_parse_required_tables(text)` — markdown tables and the heading they sit under; records the first data-row header cell as the table ID.
   - `_parse_priority_legend(text)` / `_parse_id_conventions(text)` — backlog-only, triggered by section title match.

2. **`claude-3PO/scripts/utils/validator.py`** — refactor only. Replace every `self.config.specs_*` call with a lookup on a cached `TemplateSchema` loaded from the matching template file. Existing helper methods (`_check_bold_metadata`, `_check_required_sections`, `_check_required_subsections`, backlog item parsing, JSON parsing) keep their signatures and bodies — they already take schema data as arguments. Only the data source changes. The `constants.SPECS_*` grammar constants stay (blockquote patterns, field markers) because they describe *how* to parse, not *what* shape is valid.

3. **`claude-3PO/scripts/config/config.py`** — delete the 10 `specs_*` accessor methods (lines 197–227) and delete the `specs_schemas` key handling. Add one new accessor: `templates_dir` that returns the templates directory path (already referenced elsewhere via `CLAUDE_PLUGIN_ROOT`).

4. **`claude-3PO/scripts/config/config.json`** — delete lines 192–407 (`specs_schemas` block). Keep `specs_phases`, `paths`, all other sections untouched.

5. **JSON backlog validation (`validate_backlog_json`)** — the current `json_item_statuses` enum (`Backlog, In Progress, Done, Blocked`) and `json_required_fields` are not visible in the md template. Add one small file `claude-3PO/templates/backlog-sample.json` (a minimal valid example) and derive required keys + status enum by inspecting keys and `status` values across its example stories. The existing `templates/backlog-sample.json` … let me check: there's a `backlog.json` and `backlog-sample.json` already in the templates folder — reuse whichever is authoritative rather than creating a new one.

6. **Tests (TDD-first per CLAUDE.md):**
   - New `scripts/tests/test_template_schema.py` — covers each parser: metadata, status enums, section tree, tables, priority legend, ID conventions. Uses the real template files as fixtures.
   - Rewrite `scripts/tests/test_config.py` lines 140–195 (13 schema-accessor tests) → become `test_template_schema.py` tests asserting the *parsed* schema has the same values the old tests asserted. If one of those 13 is purely checking that `config.specs_schema("unknown")` returns `{}`, delete it outright — no longer meaningful.
   - Add `test_validator_against_template.py` to cover the integration: feed a known-bad report, assert the errors match the previous schema-driven errors, so the refactor preserves behavior.

### Why parse-and-compare (user's direction)

The user's guidance was explicit: "parse the template and the agent report and then validate it by comparing it." A template parser is the minimum machinery that delivers this — no YAML frontmatter, no HTML comments, no second source. The template file the human edits *is* the contract.

---

## Critical files

- `claude-3PO/scripts/config/config.json` — delete `specs_schemas` (lines 192–407).
- `claude-3PO/scripts/config/config.py` — remove specs_* accessors (lines 197–227).
- `claude-3PO/scripts/utils/validator.py` — switch data source from config to `TemplateSchema`.
- `claude-3PO/scripts/utils/template_schema.py` — **new** module.
- `claude-3PO/scripts/utils/specs_writer.py` — no behavioral change; it only wraps validator calls.
- `claude-3PO/scripts/guardrails/agent_report_guard.py` — no change; calls into `specs_writer`.
- `claude-3PO/scripts/tests/test_config.py` — remove schema-accessor tests (lines 140–195).
- `claude-3PO/scripts/tests/test_template_schema.py` — **new**.
- `claude-3PO/scripts/tests/test_validator.py` (or equivalent) — add integration test that feeds a bad report and asserts same errors emerge via the new path.
- `claude-3PO/templates/*.md` — **no changes** (the templates are already the source of truth; we're just starting to read them).
- `claude-3PO/scripts/README.md` — remove the `specs_schemas` bullet under the config section.

## Reuse existing utilities

- `lib.extractors.extract_md_sections` — already parses `##`/`###` tree. `TemplateSchema._parse_section_tree` calls it.
- `lib.extractors.extract_bold_metadata` — already extracts `**Field:** value` pairs. `TemplateSchema._parse_metadata_block` calls it.
- `lib.extractors.extract_table` — used for reading required tables out of both template and report.
- `constants.SPECS_FIELD_MARKERS`, `SPECS_BLOCKQUOTE_PATTERNS` — keep; they describe grammar, not shape.

## Order of work (TDD)

1. Write `test_template_schema.py` against the four real templates. Assert the parsed values match the current `specs_schemas` JSON values exactly. **Red.**
2. Implement `template_schema.py` until tests pass. **Green.**
3. Write `test_validator_against_template.py` with bad-report fixtures; assert current validator (still config-driven) produces expected errors. **Baseline snapshot.**
4. Refactor `validator.py` to pull schema from `TemplateSchema`. Re-run tests — must pass identically.
5. Delete `specs_schemas` from `config.json`. Delete the 10 accessor methods from `config.py`. Delete the 13 schema tests from `test_config.py`. Run full suite.
6. Update `README.md`.

## Verification

- `pytest claude-3PO/scripts/tests/ -v` — all existing + new tests pass.
- Hand-run one known-good architecture report through `SpecsValidator.validate_architecture(...)` → `[]` (no errors).
- Hand-run one report missing section `"6. Security Architecture"` → error list includes exactly that section.
- Hand-run one backlog with a `P3` priority → error list flags the invalid priority (sourced from template's Priority Legend, not config).
- `agent_report_guard` SubagentStop happy path exercised via the existing e2e suite (`project_manager/tests/test_sync.py` is unrelated; the relevant integration lives in `scripts/tests/`).
- Confirm `git diff config.json` shows exactly the `specs_schemas` block removed and nothing else.

## Out of scope

- `plan_templates` (lines 137–154) — used by `write_guard.py`/`edit_guard.py` for the plan file, a different concern. Leave untouched.
- Moving `constants.SPECS_*` into templates — they describe grammar, not schema.
- Changing any template content.

# Plan Review: TS-001 NBA Stats API Data Ingestion (v2)

## Overall Score

- **Quality score:** 87/100 — Average of the 5 dimension scores. The plan is well-structured, technically sound, and all four previously flagged defects have been correctly addressed.
- **Confidence score:** 85/100 — The plan is detailed enough to score with high confidence. No research file was available at `.claude/research/latest-research.md`, so best-practice comparisons are drawn from CODEBASE.md and general nba_api knowledge.

## Summary

This is a focused, lean implementation plan for TS-001 covering three tasks (T-010, T-011, T-012): an NBA API client wrapper, a team stats fetcher, and Parquet storage. All four defects identified in the previous review — missing `self._headers` assignment, fragile `get_data_frames()[0]` index access, `ConnectionError` import shadowing, and absent empty DataFrame guard — are now correctly reflected in the plan. The plan is implementable without guessing on any critical path. Minor remaining gaps concern logging configuration, type annotation completeness, and an underdeveloped exception hierarchy for storage operations.

## Quality Score Breakdown

| Dimension       | Score    | Justification |
| --------------- | -------- | ------------- |
| Completeness    | 88/100   | All three tasks are covered with method signatures, logic steps, and a verification suite. Missing: `storage.py` exception handling for write failures (e.g., disk full, permission error) is not described; `fetch_team_stats.py` column normalisation steps are stated but not enumerated precisely (which columns get renamed, which are dropped). |
| Clarity         | 90/100   | Logic flow for `fetch_league_game_log` is numbered and unambiguous. The four fixed defects are annotated inline with rationale (e.g., "copy so callers can't mutate the module constant"). The `get_all_team_ids` note that it is a static call with no network cost is a useful implementation signal. Dock: `fetch_team_stats` step 3 says "lowercase columns, parse game_date, add season column" but does not specify whether other columns are renamed or dropped, leaving normalisation partially open to interpretation. |
| Feasibility     | 88/100   | Dependencies confirmed installed per CODEBASE.md (nba_api 1.11.4, pandas 3.0.2, pyarrow 22.0.0). `LeagueGameLog` with `player_or_team_abbreviation="T"` is the correct single-call pattern per CODEBASE.md endpoint table. Named accessor `endpoint.league_game_log.get_data_frame()` is valid in nba_api 1.x. Manual retry with `random.uniform` jitter is a correct substitute for `tenacity`. Minor risk: CODEBASE.md Key Implementation Decisions note still references `tenacity` for retry ("tenacity for retry with exponential backoff") — this is a stale note that contradicts the plan body which correctly states no tenacity, but it could confuse an implementer reading the context section. |
| Risk Management | 82/100   | The retry loop covers `ConnectionError` and `Timeout` with exponential backoff and jitter. The empty DataFrame guard raises a descriptive `ValueError`. After retry exhaustion a `RuntimeError` is raised. Gaps: (1) HTTP 429 (rate limit) responses from the NBA Stats API are not explicitly handled — the API can return 429 as an HTTP status rather than raising a connection exception, and the plan does not mention checking `response.status_code` or handling `requests.exceptions.HTTPError`. (2) `storage.py` has no described error handling for write failures. (3) No mention of what happens if the output directory path is a file rather than a directory. |
| Alignment       | 87/100   | Plan correctly targets T-010, T-011, T-012 only and explicitly states no existing files are modified, consistent with CODEBASE.md scope. `TDD=False` is stated and consistent with CODEBASE.md. Season string `"2024-25"` format matches CODEBASE.md. Partition path `season=YYYY-YY` matches the Parquet convention from CODEBASE.md. The stale `tenacity` reference in the CODEBASE.md context block (line 297) is a minor alignment inconsistency that the plan body correctly overrides. |
| **Overall**     | **87/100** | A high-quality, immediately implementable plan with all four prior defects resolved. Remaining gaps are minor and mostly concern error handling completeness in edge cases. |

> Note: The overall score matches the quality score stated before in **Overall Score** section.

## Strengths

- All four defects from the previous review are resolved and annotated with clear rationale directly in the plan text (lines 61, 67-68, 70).
- The named accessor `endpoint.league_game_log.get_data_frame()` is correctly preferred over the fragile positional index, and the plan notes this is the "stable API" — providing the implementer a reason not to revert it.
- The retry design separates the happy-path rate-limit sleep from the error-path backoff sleep into two distinct code paths, which is architecturally cleaner than a single sleep block.
- The `__init__` assignment list (lines 59-62) is explicit and complete, eliminating any ambiguity about instance state.
- Verification section provides three graduated checks: import-only, static data (no network), and full integration — allowing fast CI feedback without always hitting the network.
- Key Design Decisions section (lines 149-154) captures the non-obvious choices (single `LeagueGameLog` call, STATS_HEADERS reuse, no tenacity) with enough reasoning to defend them in code review.

## Weaknesses

- The `fetch_team_stats.py` normalisation step is underspecified. "Lowercase columns" does not say whether only the column names are lowercased or also string values, and does not enumerate which columns from `LeagueGameLog` are retained vs. dropped. A developer could produce a valid but inconsistent schema.
- `storage.py` error handling is entirely absent from the plan. `save_to_parquet` describes happy-path writes but gives no guidance on what exceptions to surface vs. swallow (e.g., `PermissionError`, `OSError`).
- The CODEBASE.md Key Implementation Decisions block (line 296-297) still mentions `tenacity` for retry. While the plan body correctly overrides this, the contradictory note in the context section is a maintenance risk if the context block is read independently.
- `get_all_team_ids` returns `list[int]` per the plan signature, but `nba_teams.get_teams()` returns a list of dicts where the `"id"` value is an integer — the plan does not confirm whether this dict key is always `"id"` vs. another key name, which is a minor but verifiable detail missing from the spec.

## Gaps & Risks

- HTTP 429 handling is absent — **Suggestion:** Add an explicit check for `response.status_code == 429` (or `requests.exceptions.HTTPError` with status inspection) in the retry loop. The NBA Stats API throttles aggressively and returns 429 as an HTTP response, not a connection-level exception, so the current `ConnectionError`/`Timeout` guard would not catch it. A simple `raise_for_status()` call before accessing the DataFrame, combined with catching `requests.exceptions.HTTPError`, would close this gap.
- `storage.py` write-failure behaviour is unspecified — **Suggestion:** Add a sentence stating that `OSError` and `PermissionError` should propagate uncaught (let the caller decide), or that the function should log and re-raise. Either decision is acceptable but must be stated so the implementer does not silently swallow disk errors.
- Normalisation schema is implicit — **Suggestion:** Add a small table or list to `fetch_team_stats.py` specifying the exact output column set (e.g., `team_id`, `team_abbreviation`, `game_id`, `game_date`, `matchup`, `wl`, `pts`, `season`). This prevents schema drift across seasons or `LeagueGameLog` version changes.
- Stale `tenacity` reference in CODEBASE.md context — **Suggestion:** Update the Key Implementation Decisions block in CODEBASE.md (line 296) to remove the `tenacity` mention so it matches the plan body. This is a documentation-only change but prevents future confusion.

## Recommendations

1. Add a single sentence to the `fetch_team_stats.py` section listing the retained output columns by name. This closes the normalisation gap without adding complexity.
2. Add HTTP 429 handling to the `fetch_league_game_log` retry loop — either via `raise_for_status()` + `HTTPError` catch, or an explicit status code check before calling `get_data_frame()`. This is the highest-probability failure mode when hitting the NBA Stats API.
3. Add one line to `storage.py` stating the error propagation policy for write failures (re-raise `OSError`/`PermissionError` uncaught). Even a comment in the plan is sufficient.
4. Remove the stale `tenacity` reference from the CODEBASE.md Key Implementation Decisions block to keep the context consistent with the plan body.

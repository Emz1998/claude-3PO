# Plan: TS-001 NBA Stats API Data Ingestion

## Context

Avaris is an ML-powered NBA game prediction system. The XGBoost prototype (`pipeline/model/prototype_train.py`) is complete but uses synthetic data. TS-001 implements the real data ingestion pipeline: fetch team game logs from the NBA Stats API, normalise them, and persist in Parquet format — providing the training data foundation for all downstream ML work.

**Tasks in scope:**
- T-010: NBA API client wrapper with rate limiting
- T-011: Team stats fetching for current season
- T-012: Parquet file storage

**TDD**: False — implement directly, validate by running the code.

---

## Approach

Use the `LeagueGameLog` endpoint from `nba_api` to fetch all 30 teams' game logs in a single API call per season. Wrap it in a lightweight `NBAStatsClient` class with `time.sleep`-based rate limiting and a manual retry loop with exponential backoff (no `tenacity` — not installed). Normalise the DataFrame in `fetch_team_stats.py` then persist via `storage.py` using `pandas.to_parquet` with PyArrow + Snappy compression, partitioned by season in a `season=YYYY-YY` subdirectory.

---

## Files to Modify

| Action | File | Purpose |
|---|---|---|
| Create | `pipeline/data/__init__.py` | Make `pipeline.data` a Python package |
| Create | `pipeline/data/nba_client.py` | NBA API wrapper with rate limiting + retry (T-010) |
| Create | `pipeline/data/fetch_team_stats.py` | Orchestration: fetch + normalise (T-011) |
| Create | `pipeline/data/storage.py` | Parquet read/write (T-012) |

No existing files are modified.

---

## Implementation Details

### `pipeline/data/__init__.py`
Empty file (single docstring: `"""NBA data ingestion package."""`).

---

### `pipeline/data/nba_client.py`

**Module-level constants:**
```python
from nba_api.stats.library.http import STATS_HEADERS as DEFAULT_HEADERS
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
```

**Class `NBAStatsClient`:**
```python
def __init__(self, season: str, rate_limit_delay: float = 1.0) -> None
def fetch_league_game_log(self, season: str) -> pd.DataFrame
def get_all_team_ids(self) -> list[int]
```

**`__init__` assignments:**
- `self.season = season`
- `self.rate_limit_delay = rate_limit_delay`
- `self._headers = dict(DEFAULT_HEADERS)`  ← copy so callers can't mutate the module constant
- `self._logger = logging.getLogger(__name__)`

**`fetch_league_game_log` logic:**
1. Retry loop: `for attempt in range(1, MAX_RETRIES + 1):`
2. Call `LeagueGameLog(season=season, player_or_team_abbreviation="T", headers=self._headers, timeout=60)`
3. Use named accessor: `df = endpoint.league_game_log.get_data_frame()` (stable API, not fragile index `[0]`)
4. Guard: `if df.empty: raise ValueError(f"LeagueGameLog returned empty DataFrame for season {season}")`
5. After success: `time.sleep(self.rate_limit_delay)` then `return df`
6. On `requests.exceptions.ConnectionError` or `requests.exceptions.Timeout` (fully-qualified — avoids shadowing built-in): log warning, sleep exponential backoff + `random.uniform(0, 1)` jitter, continue
7. After exhausting retries: raise `RuntimeError`

**`get_all_team_ids`:** `[t["id"] for t in nba_teams.get_teams()]` — static data, no network call.

---

### `pipeline/data/fetch_team_stats.py`

```python
def fetch_team_stats(season: str = "2024-25") -> pd.DataFrame
```

1. Instantiate `NBAStatsClient(season=season)`
2. Call `client.fetch_league_game_log(season=season)`
3. Normalise: lowercase columns, parse `game_date` to datetime, add `season` column
4. Return `df.copy()`

---

### `pipeline/data/storage.py`

```python
def save_to_parquet(df: pd.DataFrame, output_dir: str, season: str) -> str
def load_from_parquet(output_dir: str, season: str) -> pd.DataFrame
```

**Path convention:** `{output_dir}/season={season}/games.parquet`

- `save`: `path.parent.mkdir(parents=True, exist_ok=True)` then `df.to_parquet(engine="pyarrow", compression="snappy", index=False)`
- `load`: Raises `FileNotFoundError` if missing, else `pd.read_parquet(engine="pyarrow")`

---

## Verification

Run smoke tests from `/home/emhar/avaris-ai` with `.venv` activated:

```bash
# 1. Import check
python3 -c "from pipeline.data.nba_client import NBAStatsClient; print('import OK')"

# 2. Static data — no network needed
python3 -c "
from pipeline.data.nba_client import NBAStatsClient
client = NBAStatsClient(season='2024-25')
ids = client.get_all_team_ids()
assert len(ids) == 30, f'Expected 30, got {len(ids)}'
print(f'Team IDs OK: {len(ids)} teams')
"

# 3. Full integration (requires network, ~1-2 min)
python3 -c "
import logging
logging.basicConfig(level=logging.INFO)
from pipeline.data.fetch_team_stats import fetch_team_stats
from pipeline.data.storage import save_to_parquet, load_from_parquet

df = fetch_team_stats(season='2024-25')
print('Shape:', df.shape)
assert 'game_date' in df.columns
assert str(df['game_date'].dtype).startswith('datetime')
assert df['season'].iloc[0] == '2024-25'

path = save_to_parquet(df, 'pipeline/data/raw', '2024-25')
print('Written to:', path)

df2 = load_from_parquet('pipeline/data/raw', '2024-25')
assert df.shape == df2.shape
print('Smoke test PASSED')
"
```

**Expected:** 30 teams, ~1200+ rows (partial 2024-25 season), `game_date` as datetime, Parquet round-trip shape matches.

---

## Key Design Decisions

1. **`LeagueGameLog` over per-team `TeamGameLog`**: One API call returns all 30 teams — far fewer calls than looping per team.
2. **Reuse `STATS_HEADERS` from `nba_api`**: Stays current with library updates; avoids hard-coding browser User-Agent strings.
3. **Rate limiting after success, backoff in except**: Two separate `time.sleep` calls — one for rate limiting on happy path, one for retry backoff on errors.
4. **No `tenacity`**: Not installed. Manual retry loop with exponential backoff + `random.uniform` jitter is equivalent.
5. **`season` param on `fetch_league_game_log`**: Allows fetching a different season without reconstructing the client.

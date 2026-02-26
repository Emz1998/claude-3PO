# AI Discussion Scripts

Python wrappers for headless/non-interactive CLI prompting with Gemini and GPT (Codex).

## Scripts

| Script      | CLI Tool   | Purpose                                    |
| ----------- | ---------- | ------------------------------------------ |
| `gemini.py` | Gemini CLI | Headless prompting via `gemini --prompt`   |
| `gpt.py`    | Codex CLI  | Non-interactive execution via `codex exec` |

## Requirements

- Python 3.10+
- Gemini CLI installed and authenticated (for gemini.py)
- Codex CLI installed and authenticated (for gpt.py)

## gemini.py

Wrapper for Gemini CLI headless mode.

### Options

| Flag                    | Description                                  |
| ----------------------- | -------------------------------------------- |
| `-p, --prompt`          | Prompt text to send                          |
| `-o, --output-format`   | Output format: `text`, `json`, `stream-json` |
| `-m, --model`           | Model override (e.g., `gemini-2.5-flash`)    |
| `-d, --debug`           | Enable debug mode                            |
| `-y, --yolo`            | Auto-approve all actions                     |
| `--approval-mode`       | Set `auto_edit` or `full`                    |
| `--include-directories` | Include directories (comma-separated)        |
| `--stdin`               | Read input from stdin                        |
| `--extract-response`    | Extract response field from JSON output      |

### Examples

```bash
# Simple prompt
python gemini.py -p "What is machine learning?"

# Pipe file content
cat README.md | python gemini.py -p "Summarize this"

# JSON output with response extraction
python gemini.py -p "Explain code" -o json --extract-response

# Stream output with auto-approve
python gemini.py -p "Analyze project" -o stream-json -y

# Specific model
python gemini.py -p "Review this" -m gemini-2.5-pro
```

## gpt.py

Wrapper for Codex CLI (GPT) non-interactive mode.

### Options

| Flag                        | Description                                                   |
| --------------------------- | ------------------------------------------------------------- |
| `-p, --prompt`              | Prompt text to send                                           |
| `-i, --image`               | Attach image files (repeatable)                               |
| `-m, --model`               | Model override (e.g., `gpt-5-codex`)                          |
| `--oss`                     | Use local Ollama provider                                     |
| `--profile`                 | Config profile from `~/.codex/config.toml`                    |
| `-s, --sandbox`             | Sandbox: `read-only`, `workspace-write`, `danger-full-access` |
| `--full-auto`               | Automation preset (workspace-write + approvals on failure)    |
| `-y, --yolo`                | Bypass approvals and sandboxing                               |
| `-C, --cd`                  | Set working directory                                         |
| `--skip-git-repo-check`     | Allow running outside git repos                               |
| `--output-schema`           | JSON schema for response validation                           |
| `--color`                   | ANSI color: `always`, `never`, `auto`                         |
| `--json`                    | Output JSONL events                                           |
| `-o, --output-last-message` | Save final message to file                                    |
| `--search`                  | Enable web search                                             |
| `--add-dir`                 | Grant additional directories write access (repeatable)        |
| `-c, --config`              | Config override `key=value` (repeatable)                      |
| `--stdin`                   | Read prompt from stdin                                        |
| `--stream`                  | Stream output in real-time                                    |
| `--extract-response`        | Extract final assistant message from JSON                     |

### Examples

```bash
# Simple prompt
python gpt.py -p "What is machine learning?"

# With model and automation
python gpt.py -p "Review this code" --model gpt-5-codex --full-auto

# JSON output with web search
python gpt.py -p "Latest Python trends" --json --search

# Pipe input
cat file.py | python gpt.py -p "Explain this code" --stdin

# With image attachment
python gpt.py -p "Describe this diagram" -i diagram.png

# Multiple config overrides
python gpt.py -p "Fix bug" -c "timeout=60" -c "max_tokens=4096"

# Save output to file
python gpt.py -p "Generate docs" -o output.md --full-auto
```

## Common Patterns

### Code Review

```bash
# With Gemini
cat src/main.py | python gemini.py -p "Review for security issues" -o json

# With Codex
cat src/main.py | python gpt.py -p "Review for security issues" --json --stdin
```

### Generate Commit Messages

```bash
# With Gemini
git diff --cached | python gemini.py -p "Write a commit message"

# With Codex
git diff --cached | python gpt.py -p "Write a commit message" --stdin
```

### Batch Processing

```bash
# Analyze multiple files with Gemini
for f in src/*.py; do
    cat "$f" | python gemini.py -p "Find bugs" -o json > "reports/$(basename $f).json"
done

# Analyze multiple files with Codex
for f in src/*.py; do
    python gpt.py -p "Find bugs in this file" --stdin < "$f" > "reports/$(basename $f).txt"
done
```

## Output Formats

### Gemini

| Format        | Description                             |
| ------------- | --------------------------------------- |
| `text`        | Human-readable text (default)           |
| `json`        | Structured JSON with response and stats |
| `stream-json` | JSONL events streamed in real-time      |

### Codex

| Format   | Description                                                 |
| -------- | ----------------------------------------------------------- |
| Default  | Formatted text output                                       |
| `--json` | JSONL events (init, message, tool_use, tool_result, result) |

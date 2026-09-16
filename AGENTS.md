# Token-efficient tool usage

When running commands that may produce large output:

- Prefer `.agent-tools/tkrun.py` for tests, builds, linting, and verbose commands.

- Prefer `rg` over reading whole directories or large files.

- Prefer `git diff` over rereading modified files.

- For large files, inspect relevant symbols or line ranges first.

- Do not print complete large JSON files; use jq or targeted extraction.

- If a command produces large output, preserve the full output on disk and return only actionable errors and a path to the complete log.


# Agent Instructions

## Token-efficient tool usage

Use local deterministic tools before sending large amounts of data into model context.

### Command execution

For commands that may produce large output, prefer:

```bash
python .agent-tools/tkrun.py -- <command>
```

Examples:

```bash
python .agent-tools/tkrun.py -- npm test
python .agent-tools/tkrun.py -- npm run build
python .agent-tools/tkrun.py -- npm run lint
python .agent-tools/tkrun.py -- pytest
python .agent-tools/tkrun.py -- cargo test
```

The Codex PreToolUse hook may automatically wrap known verbose commands.

Do not bypass the wrapper unless the full raw output is specifically required.

### Reading files

Do not read an entire large file when a focused read is sufficient.

Prefer:

```bash
python .agent-tools/tkread.py src/example.ts --lines 100:220
```

or:

```bash
python .agent-tools/tkread.py src/example.ts --grep "fetchWeather"
```

Prefer `rg` for repository searches:

```bash
rg "certificate" src/
rg "WeatherClient" .
```

Do not recursively dump directories or large files into context.

### Git

Prefer:

```bash
git status --short
git diff --stat
git diff -- <relevant-file>
```

over rereading every modified file.

### JSON

For large JSON files, use targeted extraction when possible.

Prefer:

```bash
jq '.errors' response.json
jq '.data[:10]' response.json
jq 'keys' response.json
```

Do not print multi-megabyte JSON files directly.

### Logs

Keep complete command output on disk.

Return only:

- actionable errors
- failing tests
- useful stack traces
- warnings that require action
- final summaries
- the path to the complete log

Do not delete the complete log merely to reduce model context.

### Formatting and linting

Use deterministic tools for deterministic work.

Prefer running formatters, linters, type checkers, and tests instead of asking the model to manually inspect formatting or infer compiler errors.

### Token statistics

Token-saver numbers are estimates of model context avoided.

They are not API billing measurements and must not be described as exact API token savings.

To view statistics:

```bash
python .agent-tools/tkstats.py
```

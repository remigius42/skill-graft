# Development

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pre-commit install --install-hooks
.venv/bin/pre-commit install --hook-type commit-msg
```

The `commit-msg` hook is a separate install. Without it, commitlint never runs.

## Checks

```sh
.venv/bin/pre-commit run --all-files
```

Hooks in use: `mdformat` and `markdownlint` for Markdown, `cspell` for spelling, `ruff` and `mypy` for Python,
`check-yaml` and `check-toml` for configuration, `gitleaks` for secrets, and `commitlint` for commit messages.

A `pytest` hook joins them with the first test.

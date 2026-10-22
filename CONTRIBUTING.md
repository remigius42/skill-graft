# Development

## Setup

```sh
uv sync
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

The `commit-msg` hook is a separate install. Without it, commitlint never runs.

## Checks

```sh
uv run pre-commit run --all-files
uv run pytest
```

Hooks in use: `mdformat` and `markdownlint` for Markdown, `cspell` for spelling, `ruff` and `mypy` for Python,
`pytest` for the tests (on the default Python and on 3.11, the oldest supported), `check-yaml` and
`check-toml` for configuration, `gitleaks` for secrets, and `commitlint` for commit messages.

The tests point `HOME` at a temporary directory. The APM integration test runs the `apm` from the dev group
and is skipped when `apm` is not on `PATH`.

## Evals

`evals/graft-check/run.sh [scenario…]` runs the working copy of the `graft-check` skill headless with `claude -p` on
synthetic packages and greps its reports. It is opt-in and costs tokens, so no hook or CI job runs it; run it when the
skill changes. It needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`. Scenarios and
checks: [evals/graft-check/README.md](evals/graft-check/README.md).

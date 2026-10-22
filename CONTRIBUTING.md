# Contributing

The rules for commits, code and tests are in [AGENTS.md](AGENTS.md), and the project's terms in
[CONTEXT.md](CONTEXT.md); both hold for people as for agents.

## Setup

```sh
uv sync
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

The `commit-msg` hook is a separate install. Without it, commitlint never runs.

## Changes

A change goes through [OpenSpec](https://github.com/Fission-AI/OpenSpec), one branch per change, `feat/opsx-<change-name>`:

1. Propose it under `openspec/changes/<change-name>/` (proposal, design, specs, tasks) and wait for its approval.
1. Apply it test-first, one commit per task.
1. Archive it, which merges its specs into `openspec/specs/`. If users see the change, add its `CHANGELOG.md` entry
   in the archive commit.

Any other commit users would see, such as a direct `fix:`, adds its own entry; [AGENTS.md](AGENTS.md) has the rule.

## Checks

```sh
uv run pre-commit run --all-files
uv run pytest
```

The hooks are listed in [.pre-commit-config.yaml](.pre-commit-config.yaml).

The tests point `HOME` at a temporary directory. The APM integration test runs the `apm` from the dev group
and is skipped when `apm` is not on `PATH`.

## Evals

`evals/graft-check/run.sh [scenario…]` runs the working copy of the `graft-check` skill headless with `claude -p` on
synthetic packages and greps its reports. It is opt-in and costs tokens, so no hook or CI job runs it; run it when the
skill changes. It needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`. Scenarios and
checks: [evals/graft-check/README.md](evals/graft-check/README.md).

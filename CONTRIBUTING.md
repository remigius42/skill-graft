# Contributing

The rules for commits, code and tests are in [AGENTS.md](AGENTS.md), and the project's terms in
[CONTEXT.md](CONTEXT.md); both hold for people as for agents. How it works, and why, is mapped in
[docs/README.md](docs/README.md).

## Setup

```sh
uv sync
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

The `commit-msg` hook is a separate install. Without it, commitlint never runs.

## Changes

A change goes through [OpenSpec](https://github.com/Fission-AI/OpenSpec), one branch per change,
`feat/opsx-<change-name>`:

1. Propose it under `openspec/changes/<change-name>/` (proposal, design, specs, tasks) and wait for its approval.
1. Apply it test-first, one commit per task.
1. Archive it, which merges its specs into `openspec/specs/`. If users see the change, add its `CHANGELOG.md` entry in
   the archive commit.

Any other commit users would see, such as a direct `fix:`, adds its own entry; [AGENTS.md](AGENTS.md) has the rule.

## Checks

```sh
uv run pre-commit run --all-files
uv run pytest
```

The hooks are listed in [.pre-commit-config.yaml](.pre-commit-config.yaml).

The tests point `HOME` at a temporary directory. The APM integration test runs the `apm` from the dev group and is
skipped when `apm` is not on `PATH`.

## Tooling

The tools run at pinned versions: the hooks at a commit SHA, their `additional_dependencies` and node at a version, the
actions at a SHA, commitlint for CI in `.github/commitlint/package-lock.json`. Only what a hook itself depends on floats
within its range, such as the commitlint hook's `@commitlint/cli`. To update the hooks:

```sh
uv run pre-commit autoupdate --freeze
uv run pre-commit install-hooks
uv run pre-commit run --all-files
```

Without `--freeze`, `autoupdate` writes tags back. Dependabot opens the bumps for `.github/commitlint/`, the actions and
`uv.lock` ([.github/dependabot.yml](.github/dependabot.yml)), weekly; the `check-dependabot` hook checks that file
against its schema. Some versions move in pairs, so bump the other with it, on a Dependabot branch too. The `check-pins`
hook ([scripts/check_pins.py](scripts/check_pins.py)) fails, naming both sides, while a pair differs:

- the mypy hook's version and `mypy` in the dev group of `pyproject.toml`, then `uv lock`
- the mypy hook's `pytest` and `tomlkit` and the versions in `uv.lock`
- each `@v<version>` in `README.md`'s Installation and `version` in `pyproject.toml`, which the release commit sets
  together; and, a pair of its own, so that neither form can go missing, each `skill-graft==<version>` there and that
  same `version`
- the APM version `README.md` requires, in its text and each `apm-cli==` of its install line, and `apm-cli` in the dev
  group of `pyproject.toml`, then `uv lock`; no hook checks the rest, so measure again what
  [docs/apm-behavior.md](docs/apm-behavior.md) records, copy the hidden character classes in
  `src/skill_graft/infra/text.py` again from APM's `apm_cli/security/content_scanner.py`, and update every other mention
  of the old version (`grep -rnF '<old version>' docs src tests`)
- the commitlint hook's `@commitlint/config-conventional` and `.github/commitlint/`:
  `npm install --prefix .github/commitlint --package-lock-only --ignore-scripts --save-exact @commitlint/cli@<version> @commitlint/config-conventional@<version>`
- `node` under `default_language_version` and `node-version` in the commitlint job of `.github/workflows/ci.yml`

Nothing bumps node or the digest of the `test-root` job's container image: update them by hand, now and then.

Run `install-hooks` before the next commit: a `commit-msg` hook's environment, commitlint's, is otherwise installed
during that commit, which has overwritten the index of a worktree with the hook's own files.

## Mutation testing

See [docs/mutation-testing.md](docs/mutation-testing.md).

## Evals

`evals/graft-check/run.sh [scenario…]` runs the working copy of the `graft-check` skill headless with `claude -p` on
synthetic packages and greps its reports. It is opt-in and costs tokens, so no hook or CI job runs it; run it when the
skill changes. It needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`. Scenarios and
checks: [evals/graft-check/README.md](evals/graft-check/README.md).

`evals/graft-vet/run.sh [scenario…]` does the same for the `graft-vet` skill, with the same token and opt-in. Its
`corpus` scenario vets a labelled corpus of synthetic skills and prints a score per skill and kind; run it when the
skill or the corpus changes, and compare runs before and after. `CORPUS_SKILLS="<name>…"` runs a few skills only,
`GRAFT_VET_SCORES=<dir>` keeps each score, and `evals/graft-vet/corpus.py compare` sums kept scores scored against the
same corpus and skill. Labels, the score and how to read it: [evals/graft-vet/README.md](evals/graft-vet/README.md).

## Releasing

See [docs/releasing.md](docs/releasing.md).

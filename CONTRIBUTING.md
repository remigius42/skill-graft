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

## Evals

`evals/graft-check/run.sh [scenario…]` runs the working copy of the `graft-check` skill headless with `claude -p` on
synthetic packages and greps its reports. It is opt-in and costs tokens, so no hook or CI job runs it; run it when the
skill changes. It needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`. Scenarios and
checks: [evals/graft-check/README.md](evals/graft-check/README.md).

## Releasing

A release turns `CHANGELOG.md`'s `[Unreleased]` into a version, tagged `v<version>` and published as a GitHub release.
Only a commit CI passed is tagged, and `main` never names a version before CI has passed it.

1. Pick the version from the sections under `[Unreleased]`, by [Semantic Versioning](https://semver.org/). An entry is
   breaking when it sits under `### Removed`, or under `### Changed` and a config, command or lock users already have
   stops working as before. Before 1.0, a breaking entry raises the minor version, anything else the patch. From 1.0, a
   breaking entry raises the major version, else an `### Added` or `### Deprecated` entry the minor, else the patch.

1. Branch from an up-to-date `main`, with the version in `v` for the commands below:

   ```sh
   v=0.2.0
   git switch main && git pull --ff-only && git switch -c "release/v$v"
   ```

1. Make one commit, `chore(release): <version>`:

   - In `CHANGELOG.md`, rename `## [Unreleased]` to `## [<version>] - <today, YYYY-MM-DD>`, and add an empty
     `## [Unreleased]` above it.
   - At the end of `CHANGELOG.md`, point `[Unreleased]` at `compare/v<version>...HEAD` and add `[<version>]` comparing
     the previous tag with `v<version>`; for the first release, `[<version>]` links `releases/tag/v<version>`. Both are
     URLs under `https://github.com/remigius42/skill-graft/`. mdformat then writes the labels in lower case and sorts
     them; leave them so.
   - Set `version` in `pyproject.toml`, then run `uv lock`.

1. Push the branch, which runs CI, and wait for the run to pass:

   ```sh
   git push -u origin "release/v$v"
   gh run watch "$(gh run list --branch "release/v$v" --limit 1 --json databaseId --jq '.[0].databaseId')"
   ```

   If CI fails, fix it on the branch and push again. If `main` moved meanwhile, rebase the branch onto it, set the
   changelog date to today, and push with `--force-with-lease`.

1. Fast-forward `main` to the release commit, push it, then tag that commit and push the tag:

   ```sh
   git switch main && git merge --ff-only "release/v$v" && git push origin main
   git tag -a "v$v" -m "skill-graft $v" && git push origin "v$v"
   ```

1. Publish the GitHub release, with that version's changelog section as its notes:

   ```sh
   awk -v v="$v" 'index($0, "## [" v "]") == 1 { f = 1; next } f && (/^## \[/ || /^\[[^]]*\]: /) { exit }
     f && NF { while (n) { print ""; n-- } s = 1; print; next } f && s { n++ }' CHANGELOG.md > notes.md
   gh release create "v$v" --verify-tag --title "skill-graft $v" --notes-file notes.md && rm notes.md
   ```

1. Delete the branch: `git branch -d "release/v$v" && git push origin --delete "release/v$v"`.

A wrong tag nobody has installed yet is removed, with its release, by `gh release delete "v$v" --cleanup-tag --yes`.
Once someone may have installed it, leave it and release a fixed patch version instead.

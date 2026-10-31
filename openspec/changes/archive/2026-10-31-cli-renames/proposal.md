# Proposal

## Why

Since `build` deploys only what `skill-graft.lock` records (ADR 0009), `resolve`, `update` and the editing commands do
the vendoring; `build` resolves only to check the **Hull** against the lock, then runs APM. Its name tells users it
picks up their edits, which is the one thing it now refuses. Two option names mislead the same way: under a command
named `deploy`, `--no-install` reads as "deploy without deploying", and `--diff` promises a diff on standard output
while it writes the **Deployed diff** to a file, beside `--dry-run`, which prints the **Hull diff**. 0.4.0 breaks
already, so the names change now, in one release, with no alias.

## What Changes

- **BREAKING**: `build` is renamed `deploy`. Behavior is unchanged: it still resolves to check, refuses drift naming
  `resolve`, deploys a changed path **Source**'s **Skill** as is, and runs APM. `deploy --into <dir>` is what
  `build --into <dir>` was.
- **BREAKING**: `--no-install` is renamed `--no-apm-install`.
- **BREAKING**: `--diff <file>` is renamed `--diff-file <file>` on `update`, `resolve`, `add`, `remove`, `rename`,
  `bind` and `unbind`. The hints they print (`review:`, `apply:`) say `--diff-file`. Only `update --diff` was ever
  released; the others' arrive in this release under the new name.
- **BREAKING**: options are no longer accepted abbreviated: `--dry` for `--dry-run` is a usage error. Otherwise the old
  `--diff` would keep working as a prefix of `--diff-file`.
- **BREAKING**: `build`, `--no-install` and `--diff` exit 2 like any unknown command or option. No alias, no deprecation
  notice.
- The **Deployed diff**'s first line names no command: "each Skill's text as deployed". It is the marker by which
  skill-graft knows a file it may overwrite, and the first line 0.3.0 wrote, `` `build` `` included, still counts as
  one, so a `review.diff` an earlier release wrote is still overwritten.
- Every message, help text and doc that names the command says `deploy`: `init`'s config comment and its APM failure
  hint, the refusal hints (`run skill-graft resolve to accept it, then deploy`), README, `docs/design.md`,
  `docs/security.md`, `CONTEXT.md`, graft-check's `SKILL.md` and its eval. Where "build" means vendoring, it says so
  ("as vendored", "`resolve`"); "skill-graft builds a user's agent skills" stays.
- graft-check's throwaway build becomes a throwaway deploy (`skill-graft deploy --into <folder>`). A graft-check
  vendored before this release runs `build --into` and ends with that error until its **Source** is updated; updated
  first, the new graft-check runs `deploy --into`, which an older skill-graft refuses. So: upgrade skill-graft, then
  update its **Source**.

## Capabilities

### New Capabilities

- `deploy`: the `build` capability under its new name: deploy what the lock records, `--into`, `--no-apm-install`, the
  checks of the **Vendored copies**. Requirements move as they are, reworded for the name.

### Modified Capabilities

- `build`: every requirement removed, moved to `deploy`; the emptied capability is deleted at archive.
- `cli`: help lists `deploy`; warnings scenario; new requirements: options spelled in full, the former names refused.
- `check`: graft-check deploys `--into` throwaway folders and advises `deploy`; "Builds before reading" renamed "Checks
  with a throwaway deploy", "Never deploys" renamed "Never runs APM".
- `config`, `edit`, `hidden-characters`, `hull`, `init`, `patches`, `renames`, `scope`, `skill-discovery`: sentences and
  scenarios that name `build` name `deploy`.
- `git-sources`: likewise; "Build needs every ref" renamed "Deploy needs every ref".
- `resolve`: likewise, and `--diff` is `--diff-file`.
- `update`: likewise, and `--diff` is `--diff-file`, in its hints too.

## Impact

- Code: `src/skill_graft/cli.py` (command, options, help, `allow_abbrev`), `commands/build.py` → `commands/deploy.py`,
  `commands/scope.py`, `commands/review.py`, `commands/update.py`, `commands/edit.py`, `commands/resolve.py`,
  `commands/init_package.py`, `commands/explain.py`, docstrings and messages elsewhere in `src/`.
- Tests: `tests/commands/test_build.py` → `test_deploy.py`, `tests/cli/test_git_build.py` → `test_git_deploy.py`, and
  every test that runs `build`, `--no-install` or `--diff`.
- Skill and eval: `skills/graft-check/SKILL.md`, `skills/graft-check/reader.json`, `evals/graft-check/run.sh` and its
  README (scenarios `build-fails`, `never-built` renamed).
- Docs: README.md, docs/design.md, docs/security.md, CONTEXT.md, CHANGELOG.md. ADRs and archived changes stay as
  written.
- Users: scripts and habits that run `build`, `--no-install`, `--diff`, or an abbreviated option break.

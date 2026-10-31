# Design

## Context

See proposal.md, Why. `build` (`commands/build.py`) still runs `transaction.resolving`: it computes the **Hull**,
renders a lock, refuses one other than the recorded lock, stages the **Vendored copies** and writes the lock, then runs
`apm install`. `--into` runs the same check against the **Package**'s lock and writes into another folder. `--diff` is
added to `resolve` and the five editing commands by `cli._review_options`, to `update` in `_parser` itself (with its
description and `--expect` help naming it), and checked in `commands/review.py`. The parsers are `_Command` subclasses
of `argparse.ArgumentParser` with argparse's default `allow_abbrev=True`.

## Goals / Non-Goals

**Goals:**

- One release, 0.4.0, carries every rename; afterwards no code path knows the old names, but for the first line of a
  Deployed diff 0.3.0 wrote.

**Non-Goals:**

- `deploy` stopping to resolve, so that a path **Source**'s edit would need `resolve` first: a behavior change against
  ADR 0009, for its own change.
- `resolve` unchanged but for `--diff-file`.
- Marking the existing `[Unreleased]` entry "`build` deploys only what `skill-graft.lock` records" BREAKING.
- Rewording ADRs, archived changes or released CHANGELOG sections.

## Decisions

- **Clean break, no alias.** 0.x lets a minor release break (CONTRIBUTING.md), and 0.4.0 already does. argparse's
  `invalid choice` error lists `deploy`, which is the pointer an alias's notice would give. Considered: `build` as a
  deprecated alias for one release, warning on stderr; rejected as code, help handling and a removal task for a project
  with no known dependents.
- **`deploy --into`, not `resolve --into`.** `--into` checks the **Hull** against the **Package**'s lock as `deploy`
  does and only swaps the target; on `resolve` it would have to start refusing drift.
- **`--no-apm-install`, not `--no-install` or `--check`.** It names the subprocess skipped; `--check` would hide that it
  may still write the lock and the copies of a changed path **Source**.
- **`--diff-file`, not `--diff` or `--diff-out`.** It names what it takes; the specs already call it the Deployed diff
  file. `--diff-out` is no common CLI word.
- **`allow_abbrev=False` on `_Command`**, which every parser, the top level's and each command's (through
  `parser_class`), is. Without it `--diff` is still accepted as a prefix of `--diff-file`, and any option added later
  can break an abbreviation a user relies on.
- **The capability moves.** OpenSpec cannot rename a capability folder: `specs/deploy/spec.md` ADDs every requirement of
  `build`, reworded, and `specs/build/spec.md` REMOVEs each. Four requirement names change on the way: "Build without
  installing" → "Deploy without running APM", "Build deploys the lock" → "Deploy what the lock records", "Build into a
  folder" → "Deploy into a folder", and "Into never installs" → "Into never runs APM". The archive deletes the emptied
  `openspec/specs/build/`.
- **Scenario names in MODIFIED blocks stay.** `openspec validate` refuses a MODIFIED block whose scenario names differ
  from the main spec's. Those headers (`Build fails`, `Never built`, `Project build`, …) and the two Purpose lines that
  say build (`check`, `git-sources`) are renamed in the main specs by hand in the archive commit.
- **The Deployed diff's first line names no command, and 0.3.0's still counts.** It is the marker `review.check_target`
  knows a file it may overwrite by, and the `update` spec holds it the same in every Deployed diff skill-graft writes.
  It now says "each Skill's text as deployed", which no later rename stales; `check_target` takes a file starting with
  it or with the line 0.3.0 wrote, so a `review.diff` 0.3.0 wrote is still overwritten, not refused as one skill-graft
  did not write. Considered: keeping 0.3.0's bytes, `` `build` `` included; rejected as the first line of a file read in
  an editor naming a command that exits 2. Considered: rewording it alone; rejected for that refusal.
- **graft-check's requirements say what it does.** "Builds before reading" becomes "Checks with a throwaway deploy", and
  "Never deploys", beside it a contradiction, becomes "Never runs APM": its text already forbids `deploy` without
  `--into` and `apm`.
- **"build" as vendoring.** Where prose means the step that patches, renames and copies (`explain.py`'s "the build
  rewrites it", graft-check's "references its build got wrong", `reader.json`'s "as built"), it says "vendoring", "as
  vendored" or `resolve`. "skill-graft builds a user's agent skills", the top-level help's "Build your agent skills …"
  and `[build-system]` stay.
- **Modules follow.** `commands/build.py` → `commands/deploy.py` with `deploy()`, by `git mv` so history follows;
  `tests/commands/test_build.py` → `test_deploy.py`, `tests/cli/test_git_build.py` → `test_git_deploy.py`. The
  `lint-imports` contracts name no `build` module.

## Risks / Trade-offs

- \[A user's script runs `build` or `--diff`\] → it exits 2 naming the option and listing the commands; the CHANGELOG
  entry names each rename.
- \[A graft-check vendored before 0.4.0 runs `build --into`\] → its **Check** ends with that error; the CHANGELOG says
  to update the skill-graft **Source**, then `deploy`.
- \[The skill-graft **Source** updated before skill-graft itself\] → the new graft-check runs `deploy --into`, which
  0.3.0 refuses, and the lock's version guard does not catch a missing command; the CHANGELOG says to upgrade
  skill-graft first.
- [A mechanical replace misses or catches the wrong "build"] → before the archive, the case-insensitive greps in
  tasks.md list every `build`, `built`, `builds`, `building` and `--diff` left, each checked by hand.

## Migration Plan

Users, in this order: upgrade skill-graft; run `deploy` for `build`, `--no-apm-install` for `--no-install`,
`--diff-file` for `--diff`, and spell options in full; then update the skill-graft **Source**
(`skill-graft update skill-graft` under `init`'s alias) and `deploy`, so graft-check matches.

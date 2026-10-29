# Proposal

## Why

`update --dry-run` prints an `apply:` line even when applying would write nothing. With every tip `(unchanged)` and
`hull unchanged`, the 64-hex `--expect` value then looks like a sha that should have matched the 40-hex `ref`, and reads
like a bug. The placeholder `<digest>` doesn't help: `CONTEXT.md` calls the value a **Hull digest**.

## What Changes

- A dry run that would write nothing, where no `ref` moves and the lock it would write records what the current lock
  records, prints `nothing to apply` in place of its `apply:` line, before its `dry run:` line.
- A dry run that moves no `ref` prints the prose-suggestion line `update` prints,
  `skill-graft: <n> prose suggestion(s): run skill-graft resolve`, not `... at the new tips: update, then run ...`:
  `resolve` already sees those tips.
- `--expect`'s placeholder becomes `hull-digest`: the usage line (`--expect hull-digest`), `update`'s help, the mismatch
  error (`its hull digest is …`), `README.md` and `docs/design.md`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `update`: **Update to the hull vetted** gains the `nothing to apply` case and names `<hull-digest>`; **Selection
  errors**' scenario names `<hull-digest>`.
- `resolve`: **Prose suggestions** says the dry-run line applies only when the dry run moves a `ref`.

## Impact

- `src/skill_graft/commands/resolve.py`: `resolving` renders the lock on a dry run too and keeps the text.
- `src/skill_graft/commands/update.py`: the nothing-to-apply check, the message, the error wording, and the
  `announce_suggestions` call, which passes `dry_run` only when a `ref` moves.
- `src/skill_graft/cli.py`: the `--expect` metavar, its help, and `update`'s description.
- `README.md` (the `update` example and its usage line), `docs/design.md`; `CHANGELOG.md` at archive.
- Tests in `tests/commands/test_update.py`, `tests/commands/test_resolve.py` (a dry run now renders) and
  `tests/cli/test_cli.py` (the help).

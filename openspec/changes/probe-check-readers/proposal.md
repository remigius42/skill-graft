# Proposal

## Why

A **Check** counts as hardened only when its session runs in Claude Code and `claude --help` lists the reader flags.
Neither proves the readers work: a reader that cannot log in, or whose account has lapsed, fails, and the **Check**
learns it only after starting one per **Skill**, each named as having no report. And a user of another harness with
Claude Code installed gets no hardened **Check**, though the confinement lives in the readers, not in the session that
starts them.

## What Changes

- Before any reader starts, the **Check** runs one probe: a reader, as every reader runs, on a trivial prompt in an
  empty folder. It is hardened when the probe answers as expected, in any harness; a failed probe makes it unhardened,
  naming the probe's error, and it asks yes or no as today.
- The `CLAUDECODE` and `claude --help` tests go: the probe covers a missing `claude`, missing flags, no login and a
  lapsed account at once.
- Outside Claude Code, before the probe, the **Check** says its readers and patcher run on the user's Claude Code
  account, and probes only on a yes; on anything else it is unhardened and asks as today.
- The skill finds `reader.json` and `patcher.json` in its own folder in any harness, not through Claude Code's
  `${CLAUDE_SKILL_DIR}` alone.
- `docs/security.md`, the README's Security section and ADR 0007 say the **Check** is hardened wherever a working
  Claude Code is installed, not only in Claude Code.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `check`: "Unhardened only on the user's yes" decides hardened by the probe; a new requirement asks the user before
  readers run on their Claude Code account from another harness.

## Impact

- `skills/graft-check/SKILL.md` (step 1, the reader and patcher commands), `skills/graft-check/reader.json` (a probe
  mode).
- `tests/cli/test_check.py`: the reader's probe mode.
- `evals/graft-check/`: the `unhardened` scenario fails the probe instead of hiding `--restricted`.
- `docs/security.md`, `README.md`, `docs/adr/0007-upstream-text-is-untrusted.md`.
- `CHANGELOG.md` entry at archive.

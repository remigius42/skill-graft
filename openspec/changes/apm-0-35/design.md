# Design

## Context

skill-graft drives APM as a command and copies three things from one version of it, as `apm_cli` is no API: where each
target deploys skills (`infra/paths.py`), the **Hidden character** classes of its install check (`pipeline/hidden.py`),
and the behavior `docs/design.md` lists under "Measured APM behavior", which the code and ADR 0003 rely on. Nothing
checks the installed APM's version at run time; the README states the one supported.

Compared from the PyPI wheels and by deploying a synthetic skill for all 21 targets at both scopes (see proposal.md):
`apm_cli/security/content_scanner.py` is byte-identical, every target of 0.33.0 deploys where it did, and `grok-bot`,
new and explicit-only (not in `--target all`), deploys to `agent-data/workflows/<skill>/` under the home folder or the
project root. The deploy folders are read for one thing only: the warning when a path **Source** overlaps one.

## Goals / Non-Goals

**Goals:**

- Every claim the repository makes about APM's behavior holds for 0.35.0, measured, not assumed.

**Non-Goals:**

- Supporting both versions, or a range: skill-graft copies one version's behavior.
- Checking the installed APM's version at run time.

## Decisions

- **Pin exactly 0.35.0**, in the README and the dev group, as 0.33.0 was. A range would claim versions nobody measured.
  The alternative, `>=0.33.0,<0.36`, would also need both versions' measurements kept apart in `design.md`.
- **`check-pins` holds the two pins together**, before the bump. Dependabot bumps only `pyproject.toml` and `uv.lock`;
  without the pair, its next APM PR goes green with the README still naming the old version. Added first, the pair
  passes at 0.33.0 and makes the bump move both.
- **Measure before changing code.** The first task re-runs every behavior `docs/design.md` lists, at both scopes, with
  `HOME` a scratch directory, by a script kept out of the repository as the 0.33.0 measurement was; `design.md` records
  the results. The 3 APM integration tests already pass with 0.35.0 (Dependabot PR #6), so the main path is known to
  hold; the measurement covers what they do not: the failure modes, pruning, the manifest's entries, the default folder.
- **`agent-data/workflows` joins both tuples, last.** The tuples are sorted, and a dotted name sorts first. No other
  code changes: the overlap check walks the tuples. Its comment names the target, as the folder does not say whose it
  is.
- **No migration, and no BREAKING mark.** A user on 0.33.0 deploys exactly as before: what skill-graft does with APM did
  not change, only the version it is measured against. The CHANGELOG, under Changed, says to install 0.35.0, and that a
  path **Source** overlapping `agent-data/workflows` now gets the deploy folder warning.

## Risks / Trade-offs

- [A measured behavior differs in 0.35.0] → It is named in `design.md`; if skill-graft relies on it, the change stops
  for a new task, and the proposal and specs gain it before any code depends on it.
- \[`openclaw` deploys nothing without `~/.openclaw`, in both versions\] → Out of scope, unchanged; `.openclaw/skills`
  stays in `DEPLOY_FOLDERS`, as APM's target names it.
- [A user keeps 0.33.0] → Works as before; the warning for `agent-data/workflows` simply never matters to them.
- \[`agent-data/` is a generic name: a **Source** containing `<project>/agent-data/workflows` warns though the user may
  never target `grok-bot`\] → Accepted: a **Source** containing `~/.claude/skills` warns the same way without the user
  deploying to Claude, and a warning blocks nothing.

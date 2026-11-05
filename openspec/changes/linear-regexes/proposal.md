# Proposal

## Why

A `SKILL.md` whose `name:` line holds a long run of whitespace hangs skill-graft: the comment pattern, `\s+#.*$`, takes
quadratic time on it, 26 s for 100 000 spaces. **Upstream** text is untrusted (ADR 0007), so any **Source** can stall
every command that discovers its **Skills**. Every other pattern over **Upstream** text runs in linear time today, by
care alone; nothing keeps the next one from slipping, and nothing shows whether the tests pin down what each pattern
matches.

## What Changes

- The comment pattern starts only where a run of whitespace starts, in `discovery.py` and in `apm.py`'s scan of
  `apm.yml`: a `name:` line of any length is read in linear time, with the same name as before.
- Every regex that reads **Upstream** text gets a test in `tests/`: an input of about 100 000 characters shaped to make
  it backtrack, done within one second. A guard test fails on a compiled pattern in those modules that has none.
- ADR 0011: regexes over **Upstream** text run in linear time, not under size caps or timeouts.
- The **Vet** flags one- and two-digit world-writable `chmod` modes (`chmod 77`, `chmod 2`), which it missed: a gap the
  mutation harness found.
- An opt-in mutation harness, `mutation/`, run as `uv run python -m mutation`, never in hooks or CI. It mutates each
  security-relevant pattern (the **Vet**'s, **Reference** finding, the `name:` comment, `skill-graft.toml` names and
  URLs, **Hidden character** classes), runs the test files of each module holding the pattern against each mutant, and
  exits 1 on a surviving mutant not listed, with its reason, in `mutation/equivalent.toml`.

## Capabilities

### New Capabilities

None: the linear-time rule binds the code, not what a user sees, and lives in ADR 0011.

### Modified Capabilities

- `skill-discovery`: the Skill name requirement gains a scenario: a `name:` line holding a long run of whitespace
  resolves at once.

## Impact

- Code: `src/skill_graft/pipeline/discovery.py`, `src/skill_graft/infra/apm.py` (one pattern each);
  `src/skill_graft/pipeline/vet.py`'s `_OCTAL`, which the harness showed missing one- and two-digit modes.
- Tests: a linear-time registry and guard in `tests/`, 56 entries, and a `linear_time` marker; tests killing the
  harness's survivors in the target modules' test files.
- New: `mutation/` (harness, `equivalent.toml`), `docs/adr/0011-*.md`, two `Fixed` entries in `CHANGELOG.md`.
- No new runtime or dev dependency; mutmut stays out, for a later decision.

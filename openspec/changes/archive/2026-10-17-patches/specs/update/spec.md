# Spec Delta

## ADDED Requirements

### Requirement: Patches at the new tips

A patch failing at the new tips SHALL fail `update` as any resolution error does, leaving the TOML and the lock
unchanged, and the error SHALL name each failing **Skill**'s **Upstream** folder at the tip, to redo the patch against.
When that folder is in a dry run's temporary cache, it SHALL say instead to run `update` without `--dry-run` to fetch
the tip.

#### Scenario: Patch fails at the tip

- **WHEN** the new tip of `mp` changes the lines a patch to `mp/tdd` replaces
- **THEN** `update` exits non-zero naming the hunk and `mp/tdd`'s folder in the cache export of the new tip, and
  `skill-graft.toml` and `skill-graft.lock` keep their bytes

#### Scenario: Patch redone

- **WHEN** after that failure the user rewrites the patch against the named folder and runs `update` again
- **THEN** `update` moves `mp`'s `ref` to the tip and writes the lock

#### Scenario: Dry run with a failing patch

- **WHEN** the new tip was not cached before, a patch fails there, and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the hunk and saying to run `update` without `--dry-run` to fetch the tip

### Requirement: Hull diff when patches fail at the current refs

When today's **Patches** fail at the current `ref`s, the hull diff SHALL say only
`no previous hull to compare (patches fail at the current refs)`, without the failing hunks, and `update` SHALL go on as
when the current `ref`s do not resolve. When another error stops the walk there as well, it SHALL say that the current
`ref`s do not resolve, that patches fail there, and the other error.

#### Scenario: Patch already rewritten for the tip

- **WHEN** the user rewrote a patch against the new tip of `mp` and runs `update`
- **THEN** it prints `no previous hull to compare (patches fail at the current refs)`, moves `mp`'s `ref` and writes the
  lock

#### Scenario: Another error at the current refs

- **WHEN** at the current `ref`s a patch to **Entry** `mp/tdd` fails, and **Entry** `mp/notes` calls `/y`, bound to
  `mp/x`, which only the new tip has
- **THEN** `update` prints that the current `ref`s do not resolve, that patches fail there, and names `mp/x`; it moves
  `mp`'s `ref`

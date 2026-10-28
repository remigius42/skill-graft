## MODIFIED Requirements

### Requirement: Resolve before writing

`update` SHALL resolve the **Hull** as `build` does, with each selected **Source** at its new tip and every other
at its current `ref`. Only when that succeeds SHALL it write `skill-graft.lock`, always, and `skill-graft.toml`,
when a `ref` moved. On
failure it SHALL exit non-zero with the resolution error and the shas it would have written, leaving the TOML
and the lock unchanged. When writing the lock fails or is interrupted after the TOML was written, it SHALL
restore the TOML's bytes; if that fails too, a notice SHALL name the TOML and the error, and the original error
SHALL be the one reported. `update` SHALL NOT vendor or run `apm`.

#### Scenario: Entry gone upstream

- **WHEN** `mp/tdd` is an **Entry** and the new tip of `mp` has no skill `tdd`
- **THEN** `update` exits non-zero naming `mp/tdd`, prints the new sha, and leaves `skill-graft.toml` byte for
  byte unchanged

#### Scenario: Reference turns ambiguous upstream

- **WHEN** at the new tip of `x`, a skill `notes` appears that `own` also has, and a **Hull** **Skill** in `mp`
  calls `/notes`
- **THEN** `update` exits non-zero naming `/notes` and both **Skill IDs**, and leaves the TOML and lock unchanged

#### Scenario: Subdirectory gone upstream

- **WHEN** `[sources.cp]` has `subdirectory = "pstack/skills"`, and the new tip of `cp` no longer has
  `pstack/skills`
- **THEN** `update` exits non-zero naming `cp`, `pstack/skills` and the new sha, and leaves the TOML and lock
  unchanged

#### Scenario: Lock write fails

- **WHEN** `update` moves `mp`'s `ref` to B and writing `skill-graft.lock` fails
- **THEN** `update` exits 1 naming the error, and `skill-graft.toml` and the lock are byte for byte as before

#### Scenario: Lock write interrupted

- **WHEN** `update` moves `mp`'s `ref` to B and the user presses Ctrl-C while `skill-graft.lock` is written
- **THEN** `skill-graft.toml` and the lock are byte for byte as before

#### Scenario: Lock follows the TOML

- **WHEN** `update` moves `mp`'s `ref` to B
- **THEN** `skill-graft.lock` records B

#### Scenario: Lock written though no ref moved

- **WHEN** no `ref` moves, but a path **Source**'s skill changed since the last lock
- **THEN** `skill-graft.toml` keeps its bytes, and `skill-graft.lock` holds the new hash

#### Scenario: No deploy

- **WHEN** `update` succeeds
- **THEN** `.apm/skills/` is unchanged and `apm` is not run

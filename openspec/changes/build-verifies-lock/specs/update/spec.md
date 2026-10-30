## MODIFIED Requirements

### Requirement: Resolve before writing

`update` SHALL resolve the **Hull** as `build` does, with each selected **Source** at its new tip and every other at its
current `ref`. Only when that succeeds SHALL it vendor `.apm/skills/` and write `skill-graft.lock`, always, together as
`resolve` does, and `skill-graft.toml`, when a `ref` moved. On failure it SHALL exit non-zero with the resolution error
and the shas it would have written, leaving the TOML, the lock and `.apm/skills/` unchanged. When writing the lock fails
or is interrupted after the TOML was written, it SHALL restore the TOML's bytes and `.apm/skills/`; if restoring the
TOML fails too, a notice SHALL name the TOML and the error, and the original error SHALL be the one reported. `update`
SHALL NOT run `apm`.

#### Scenario: Entry gone upstream

- **WHEN** `mp/tdd` is an **Entry** and the new tip of `mp` has no skill `tdd`
- **THEN** `update` exits non-zero naming `mp/tdd`, prints the new sha, and leaves `skill-graft.toml` byte for byte
  unchanged

#### Scenario: Reference turns ambiguous upstream

- **WHEN** at the new tip of `x`, a skill `notes` appears that `own` also has, and a **Hull** **Skill** in `mp` calls
  `/notes`
- **THEN** `update` exits non-zero naming `/notes` and both **Skill IDs**, and leaves the TOML and lock unchanged

#### Scenario: Subdirectory gone upstream

- **WHEN** `[sources.cp]` has `subdirectory = "pstack/skills"`, and the new tip of `cp` no longer has `pstack/skills`
- **THEN** `update` exits non-zero naming `cp`, `pstack/skills` and the new sha, and leaves the TOML and lock unchanged

#### Scenario: Lock write fails

- **WHEN** `update` moves `mp`'s `ref` to B and writing `skill-graft.lock` fails
- **THEN** `update` exits 1 naming the error, and `skill-graft.toml`, the lock and `.apm/skills/` are byte for byte as
  before

#### Scenario: Lock write interrupted

- **WHEN** `update` moves `mp`'s `ref` to B and the user presses Ctrl-C while `skill-graft.lock` is written
- **THEN** `skill-graft.toml`, the lock and `.apm/skills/` are byte for byte as before

#### Scenario: Lock follows the TOML

- **WHEN** `update` moves `mp`'s `ref` to B
- **THEN** `skill-graft.lock` records B

#### Scenario: Lock written though no ref moved

- **WHEN** no `ref` moves, but a path **Source**'s skill changed since the last lock
- **THEN** `skill-graft.toml` keeps its bytes, and `skill-graft.lock` holds the new hash

#### Scenario: No deploy

- **WHEN** `update` moves `mp`'s `ref` to B, where `mp/tdd` changed
- **THEN** `.apm/skills/tdd/` holds `mp/tdd` at B, and `apm` is not run

### Requirement: Dry run writes nothing

`update --dry-run` SHALL do everything `update` does, printing the same lines and errors and exiting with the same code,
but SHALL write neither `skill-graft.toml`, `skill-graft.lock`, `.apm/skills/` nor the cache, nor anything outside a
temporary folder it removes before exiting, except the **Deployed diff** file `--diff` names. It SHALL read what the
cache already holds, and contact a remote exactly when `update` would. It SHALL say that the TOML and the lock were not
written.

#### Scenario: Dry run

- **WHEN** the default branch has moved and the user runs `update --dry-run`
- **THEN** it prints the new sha and `dry run: skill-graft.toml and skill-graft.lock not written`, and
  `skill-graft.toml`, `skill-graft.lock`, `.apm/skills/` and the cache folder are unchanged

#### Scenario: Dry run with an unreachable unselected source

- **WHEN** `b`'s `ref` is in the cache, `b`'s remote is unreachable, and the user runs `update a --dry-run`
- **THEN** it succeeds as `update a` would, reading `b` from the cache

#### Scenario: Dry run with a failing entry

- **WHEN** an **Entry** is gone at the new tip and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the **Entry**, as `update` would

#### Scenario: Dry run with an edited copy

- **WHEN** `.apm/skills/tdd/SKILL.md` was edited and the user runs `update --dry-run`
- **THEN** it exits 1 naming `.apm/skills/tdd` before contacting any remote, as `update` would

#### Scenario: Dry run after a killed run

- **WHEN** a killed `resolve` left `.apm/skills.old/` and `.apm/skills.new/` beside `.apm/skills/`, and the user runs
  `update --dry-run`
- **THEN** `.apm/skills/`, `.apm/skills.old/` and `.apm/skills.new/` are as before

#### Scenario: Dry run with a diff file

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds `mp/tdd`'s **Deployed diff**, and `skill-graft.toml`, `skill-graft.lock` and the cache
  folder are unchanged

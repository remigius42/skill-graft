# resolve Specification

## Purpose

`skill-graft resolve` computes the **Hull**, records its provenance in `skill-graft.lock`, and shows the user
why each **Skill** is in it.

## Requirements

### Requirement: Resolve command

`skill-graft resolve` SHALL compute the **Hull** from `skill-graft.toml`, write `skill-graft.lock`, print the
tree to standard output and the warnings to standard error, and exit 0. It SHALL NOT write `skill-graft.toml`,
`.apm/skills/`, or run `apm`. Like `build`, it SHALL fail on any git **Source** without `ref`.

#### Scenario: Resolve succeeds

- **WHEN** the user runs `skill-graft resolve` and every **Reference** resolves
- **THEN** it exits 0, `skill-graft.lock` exists, and `.apm/skills/` and `skill-graft.toml` are unchanged

#### Scenario: Resolution error

- **WHEN** a **Reference** matches several other **Sources** and no **Bind**
- **THEN** `resolve` exits non-zero and leaves any existing `skill-graft.lock` unchanged

### Requirement: Never moves a ref

`resolve` SHALL read each git **Source** at its `ref` exactly, contacting the remote only when that commit is
missing from the cache.

#### Scenario: Upstream moved on

- **WHEN** `ref` names cached commit A and the remote's branch is at B
- **THEN** `resolve` reads A, does not contact the remote, and the lock records A

### Requirement: Lock content

`skill-graft.lock`, a TOML file at `~/.apm/skill-graft/skill-graft.lock` even when `skill-graft.toml` is a
symlink, SHALL record: each declared **Source**'s alias with
its URL and `ref`, or its resolved folder; each **Hull** **Skill**'s **Skill ID**, whether it is an **Entry**,
and a SHA-256 hash of its folder as vendored; and each edge: from, to, kind (`slash` or `skill-tool`), and
`bind = true` when a **Bind** decided it. One edge per from, to, kind and `bind`.

#### Scenario: Edges with kinds

- **WHEN** `mp/tdd` calls `/grilling` and `Skill(notes)`, and `[bind]` has `"mp/notes" = "own/notes"`
- **THEN** the lock holds edges `mp/tdd` → `mp/grilling` of kind `slash`, and `mp/tdd` → `own/notes` of kind
  `skill-tool` with `bind = true`

#### Scenario: Bound and default edge to one skill

- **WHEN** `mp/tdd` calls `/g`, bound by `"mp/g" = "own/notes"`, and `/notes`, resolved by default to
  `own/notes`
- **THEN** the lock holds two `slash` edges `mp/tdd` → `own/notes`, one with `bind = true`, and the tree shows
  both

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink into another folder
- **THEN** `resolve` writes `~/.apm/skill-graft/skill-graft.lock`, and nothing in that other folder

#### Scenario: Hash follows content

- **WHEN** `resolve` runs twice and only a file inside `own/notes` changed in between
- **THEN** only the hash of `own/notes` differs between the two locks

### Requirement: Lock is deterministic

The same TOML, **Source** contents and **Source** folders SHALL give a byte-identical lock, whenever it is
written: no timestamps, everything sorted. A path **Source**'s resolved folder is part of the input, so the lock
differs across machines whose folders differ. The lock SHALL be replaced atomically.

#### Scenario: Same input

- **WHEN** `resolve` runs twice with nothing changed
- **THEN** both locks are byte for byte equal

### Requirement: The lock is output only

No command SHALL read `skill-graft.lock` to decide anything: deleting or editing it SHALL change no command's
result.

#### Scenario: Lock edited by hand

- **WHEN** the user edits the lock to name another commit and runs `build`
- **THEN** `build` vendors the skills at the TOML's `ref`, and rewrites the lock

### Requirement: Tree output

`resolve` SHALL print the **Hull** in the style of `cargo tree`: each **Entry** at the top level in TOML order,
expanded there; under each **Skill**, one line per edge naming the **Skill** and the **Reference** (`/name`,
`Skill(name)`, plus `bind` when a **Bind** decided it). A **Skill** SHALL be expanded once, at its first
depth-first line; its later lines, and any nested line for an **Entry**, SHALL end in `(*)` and not expand.

#### Scenario: Tree

- **WHEN** `mp/tdd` calls `/grilling`, `/notes` and `Skill(x)` (bound to `own/x`), and `mp/grilling` calls
  `/notes` and `/tdd`

- **THEN** `resolve` prints

  ```text
  mp/tdd
  ├── mp/grilling (/grilling)
  │   ├── mp/notes (/notes)
  │   └── mp/tdd (/tdd) (*)
  ├── mp/notes (/notes) (*)
  └── own/x (Skill(x), bind)
  ```

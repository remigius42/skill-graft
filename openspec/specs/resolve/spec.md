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
and a SHA-256 hash of its folder as vendored; and each edge: from, to, kind (`slash`, `skill-tool` or `prose`),
and `bind = true` when a **Bind** decided it. One edge per from, to, kind and `bind`.

#### Scenario: Edges with kinds

- **WHEN** `mp/tdd` calls `/grilling` and `Skill(notes)`, and `[bind]` has `"mp/notes" = "own/notes"`
- **THEN** the lock holds edges `mp/tdd` → `mp/grilling` of kind `slash`, and `mp/tdd` → `own/notes` of kind
  `skill-tool` with `bind = true`

#### Scenario: Bound and default edge to one skill

- **WHEN** `mp/tdd` calls `/g`, bound by `"mp/g" = "own/notes"`, and `/notes`, resolved by default to
  `own/notes`
- **THEN** the lock holds two `slash` edges `mp/tdd` → `own/notes`, one with `bind = true`, and the tree shows
  both

#### Scenario: Prose edge

- **WHEN** `mp/tdd` calls `/grilling` and mentions `` `grilling` ``
- **THEN** the lock holds edges `mp/tdd` → `mp/grilling` of kinds `slash` and `prose`

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink into another folder
- **THEN** `resolve` writes `~/.apm/skill-graft/skill-graft.lock`, and nothing in that other folder

#### Scenario: Hash follows content

- **WHEN** `resolve` runs twice and only a file inside `own/notes` changed in between
- **THEN** only the hash of `own/notes` differs between the two locks

### Requirement: Lock is deterministic

The same TOML, **Source** contents and **Source** folders SHALL give a byte-identical lock, whenever it is
written: no timestamps, everything sorted except a **Skill**'s `patches`, which keep their apply order. A path
**Source**'s resolved folder and the cache's location are part of the input, so the lock differs across machines
whose folders differ. The lock SHALL be replaced atomically.

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
expanded there; under each **Skill**, one line per edge naming the **Skill** and the **Reference** as written
upstream (`/name`, `Skill(name)`, `` `name` `` or `name` plus `prose`, plus `bind` when a **Bind** decided it). A
renamed **Skill** SHALL be named `<skill id> as <deployed name>` on every line, and a patched one SHALL be
followed by `(patched)` on every line. A `prose` edge SHALL have a line
only when the build rewrites it: its target's **Deployed name** differs from the name written. A **Skill** SHALL
be expanded once, at its first depth-first line; its later lines, and any nested line for an **Entry**, SHALL end
in `(*)` and not expand.

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

#### Scenario: Renames marked

- **WHEN** `mp/tdd` calls `/grilling` and mentions `` `grilling` `` and `` `notes` ``, `[rename]` has
  `"mp/tdd" = "mp-tdd"` and `"mp/grilling" = "mp-grilling"`, and `mp/notes` is an unrenamed **Entry**

- **THEN** `resolve` prints

  ```text
  mp/tdd as mp-tdd
  ├── mp/grilling as mp-grilling (/grilling)
  └── mp/grilling as mp-grilling (`grilling`, prose) (*)
  mp/notes
  ```

#### Scenario: Patches marked

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, `[patches]` names `mp/tdd` and `mp/grilling`, and `[rename]`
  has `"mp/grilling" = "mp-grilling"`

- **THEN** `resolve` prints

  ```text
  mp/tdd (patched)
  └── mp/grilling as mp-grilling (patched) (/grilling)
  ```

#### Scenario: Bound prose shown

- **WHEN** **Entry** `mp/tdd` calls `/notes` and mentions `` `notes` ``, `[bind]` has `"mp/notes" = "own/grill"`,
  and no rename names `own/grill`

- **THEN** `resolve` prints

  ```text
  mp/tdd
  ├── own/grill (/notes, bind)
  └── own/grill (`notes`, prose, bind) (*)
  ```

### Requirement: Lock records renames and suggestions

The lock SHALL record each renamed **Hull** **Skill**'s `deployed` name, and each suggested **Skill** with the
**Skill IDs** mentioning it, sorted. Each hash SHALL cover the folder as vendored, after renaming and rewriting,
so `resolve` and `build` write the same lock for the same input.

#### Scenario: Renamed skill

- **WHEN** `[rename]` has `"mp/grilling" = "mp-grilling"`
- **THEN** the lock's entry for `mp/grilling` holds `deployed = "mp-grilling"`, and entries of unrenamed
  **Skills** hold no `deployed`

#### Scenario: Suggestion recorded

- **WHEN** `mp/tdd` and `mp/grilling` mention `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** the lock holds one suggestion `mp/diagnosing-bugs` from `mp/grilling` and `mp/tdd`

#### Scenario: Rename changes the hash

- **WHEN** `resolve` runs, then `[rename]` gets `"mp/grilling" = "mp-grilling"` and it runs again, `mp/tdd`
  calling `/grilling`
- **THEN** the hashes of `mp/grilling` and `mp/tdd` differ between the two locks

#### Scenario: Resolve and build agree

- **WHEN** the user runs `resolve`, saves the lock, then runs `build --no-install`, with renames declared
- **THEN** both locks are byte for byte equal

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to accept it
(`skill-graft add <skill id>`, named in the header), sorted, on standard output. `build` SHALL NOT print suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a header naming `skill-graft add`, then a line naming
  `mp/diagnosing-bugs` and `mp/tdd`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone

### Requirement: Lock records upstream folders and patches

The lock SHALL record each **Hull** **Skill**'s `upstream` folder, absolute: the folder its **Patches** apply to,
in the cache export at the `ref` or in a path **Source**. A patched **Skill** SHALL also record its `patches`,
as written in the TOML, in apply order. Each hash SHALL cover the folder as vendored, **Patches** applied, so
`resolve` and `build` write the same lock for the same input.

#### Scenario: Upstream recorded

- **WHEN** `mp` is a git **Source** at `ref` A and `own` a path **Source**, and `mp/tdd` and `own/chisel` are in
  the **Hull**
- **THEN** `mp/tdd`'s `upstream` is its folder in the cache export of A, and `own/chisel`'s its folder under
  `own`'s path

#### Scenario: Patches recorded

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/b.patch", "patches/a.patch"]`
- **THEN** the lock's entry for `mp/tdd` holds `patches = ["patches/b.patch", "patches/a.patch"]`, and entries of
  unpatched **Skills** hold no `patches`

#### Scenario: Patch changes the hash

- **WHEN** `resolve` runs, then a patch to `mp/tdd` is declared and it runs again
- **THEN** the hash of `mp/tdd` differs between the two locks, and its `upstream` does not

#### Scenario: Resolve and build agree with patches

- **WHEN** the user runs `resolve`, saves the lock, then runs `build --no-install`, with patches declared
- **THEN** both locks are byte for byte equal

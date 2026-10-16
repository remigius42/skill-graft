# Spec Delta

## ADDED Requirements

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

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to
accept it (add its **Skill ID** to `entries`), sorted, on standard output. `build` SHALL NOT print suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a line naming `mp/diagnosing-bugs`, `mp/tdd`, and `entries`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone

## MODIFIED Requirements

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

### Requirement: Tree output

`resolve` SHALL print the **Hull** in the style of `cargo tree`: each **Entry** at the top level in TOML order,
expanded there; under each **Skill**, one line per edge naming the **Skill** and the **Reference** as written
upstream (`/name`, `Skill(name)`, `` `name` `` plus `prose`, plus `bind` when a **Bind** decided it). A renamed
**Skill** SHALL be named `<skill id> as <deployed name>` on every line. A `prose` edge SHALL have a line only when
its target is renamed. A **Skill** SHALL be expanded once, at its first depth-first line; its later lines, and
any nested line for an **Entry**, SHALL end in `(*)` and not expand.

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

# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Lock is deterministic

The same TOML, **Source** contents and **Source** folders SHALL give a byte-identical lock, whenever it is
written: no timestamps, everything sorted except a **Skill**'s `patches`, which keep their apply order. A path
**Source**'s resolved folder and the cache's location are part of the input, so the lock differs across machines
whose folders differ. The lock SHALL be replaced atomically.

#### Scenario: Same input

- **WHEN** `resolve` runs twice with nothing changed
- **THEN** both locks are byte for byte equal

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

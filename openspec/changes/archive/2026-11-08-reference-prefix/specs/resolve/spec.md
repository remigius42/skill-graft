## MODIFIED Requirements

### Requirement: Lock content

`skill-graft.lock`, a TOML file at `~/.apm/skill-graft/skill-graft.lock` even when `skill-graft.toml` is a symlink,
SHALL record: each declared **Source**'s alias with its URL, `ref` and `subdirectory` when set, or its resolved folder
(in project scope relative to the **Package** when inside the project root, else its `path` without empty or `.`
segments when that starts with `~/` and has no `..` segment, else absolute); each **Hull** **Skill**'s **Skill ID**,
whether it is an **Entry**, and a SHA-256 hash of its folder as vendored; the config's `reference-prefix`, top-level
after `version`, only when set; and each edge: from, to, kind (`slash`, `skill-tool` or `prose`), and `bind = true` when
a **Bind** decided it. One edge per from, to, kind and `bind`.

#### Scenario: Edges with kinds

- **WHEN** `mp/tdd` calls `/grilling` and `Skill(notes)`, and `[bind]` has `"mp/notes" = "own/notes"`
- **THEN** the lock holds edges `mp/tdd` → `mp/grilling` of kind `slash`, and `mp/tdd` → `own/notes` of kind
  `skill-tool` with `bind = true`

#### Scenario: Bound and default edge to one skill

- **WHEN** `mp/tdd` calls `/g`, bound by `"mp/g" = "own/notes"`, and `/notes`, resolved by default to `own/notes`
- **THEN** the lock holds two `slash` edges `mp/tdd` → `own/notes`, one with `bind = true`, and the tree shows both

#### Scenario: Prose edge

- **WHEN** `mp/tdd` calls `/grilling` and mentions `` `grilling` ``
- **THEN** the lock holds edges `mp/tdd` → `mp/grilling` of kinds `slash` and `prose`

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink into another folder
- **THEN** `resolve` writes `~/.apm/skill-graft/skill-graft.lock`, and nothing in that other folder

#### Scenario: Hash follows content

- **WHEN** `resolve` runs twice and only a file inside `own/notes` changed in between
- **THEN** only the hash of `own/notes` differs between the two locks

#### Scenario: Project source inside the project

- **WHEN** in project scope `[sources.own]` has `path = "../../skills"`
- **THEN** the lock records `own`'s path as `../../skills`, the same on every machine

#### Scenario: Project source outside the project

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"`
- **THEN** the lock records `own`'s path as `~/skills`

#### Scenario: Home path normalized

- **WHEN** in project scope `[sources.own]` has `path = "~/skills/"`, `path = "~//skills"` or `path = "~/./skills"`
- **THEN** the lock records `own`'s path as `~/skills`

#### Scenario: Project source under a symlinked home folder

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"`, and `~/skills` is a symlink to a folder outside the
  home folder
- **THEN** the lock records `own`'s path as `~/skills`

#### Scenario: Project source inside the project written with home

- **WHEN** in project scope the project root is `~/repo` and `[sources.own]` has `path = "~/repo/skills"`
- **THEN** the lock records `own`'s path as `../../skills`

#### Scenario: Project source outside the project and home

- **WHEN** in project scope `[sources.own]` has `path = "/opt/skills"`, a relative path leading outside the project
  root, the home folder's `skills` folder written out absolute, `~alice/skills`, `~/../shared`, or `~/x/../skills`
- **THEN** the lock records `own`'s path as the absolute folder

#### Scenario: User source under home

- **WHEN** in user scope `[sources.own]` has `path = "~/skills"`
- **THEN** the lock records `own`'s path as the absolute folder

#### Scenario: Subdirectory recorded

- **WHEN** `[sources.cp]` has `git`, `ref` and `subdirectory = "pstack/skills"`, and `[sources.mp]` has no
  `subdirectory`
- **THEN** the lock's table for `cp` holds `subdirectory = "pstack/skills"`, and the one for `mp` holds no
  `subdirectory`

#### Scenario: Reference prefix recorded

- **WHEN** `reference-prefix = "foo:"`
- **THEN** the lock holds `reference-prefix = "foo:"` after `version`, and without the key the lock holds no
  `reference-prefix` and is byte for byte as before

## MODIFIED Requirements

### Requirement: Lock content

`skill-graft.lock`, a TOML file at `~/.apm/skill-graft/skill-graft.lock` even when `skill-graft.toml` is a symlink,
SHALL record: each declared **Source**'s alias with its URL, `ref` and `subdirectory` when set, or its resolved folder
(in project scope relative to the **Package** when inside the project root, else its `path` without empty or `.`
segments when that starts with `~/` and has no `..` segment, else absolute); each **Hull** **Skill**'s **Skill ID**,
whether it is an **Entry**, and a SHA-256 hash of its folder as vendored; and each edge: from, to, kind (`slash`,
`skill-tool` or `prose`), and `bind = true` when a **Bind** decided it. One edge per from, to, kind and `bind`.

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

### Requirement: Lock is deterministic

The same TOML, **Source** contents and **Source** folders SHALL give a byte-identical lock, whenever it is written: no
timestamps, everything sorted except a **Skill**'s `patches`, which keep their apply order. A path **Source**'s folder
recorded absolute and the cache's location are part of the input, so the lock differs across machines whose folders
differ. The lock SHALL be replaced atomically.

#### Scenario: Same input

- **WHEN** `resolve` runs twice with nothing changed
- **THEN** both locks are byte for byte equal

### Requirement: Lock records upstream folders and patches

The lock SHALL record each **Hull** **Skill**'s `upstream` folder relative to its **Source**'s root, in either
**Scope**: the folder its **Patches** apply to, in the cache export at the `ref` or in a path **Source**. A git
**Source**'s root is the repository's, so `upstream` includes any `subdirectory`. A patched **Skill** SHALL also record
its `patches`, as written in the TOML, in apply order. Each hash SHALL cover the folder as vendored, **Patches**
applied, so `resolve` and `deploy` write the same lock for the same input.

#### Scenario: Upstream recorded

- **WHEN** `mp` is a git **Source** at `ref` A and `own` a path **Source**, `mp/tdd` is at `skills/tdd` in `mp` and
  `own/chisel` at `chisel` in `own`, and both are in the **Hull**
- **THEN** `mp/tdd`'s `upstream` is `skills/tdd` and `own/chisel`'s is `chisel`

#### Scenario: Skill at the source root

- **WHEN** a path **Source**'s folder itself holds `SKILL.md`
- **THEN** that **Skill**'s `upstream` is `.`

#### Scenario: Upstream under a subdirectory

- **WHEN** `[sources.cp]` has `subdirectory = "pstack/skills"`, `cp/tdd` is at `pstack/skills/tdd` in the repository,
  and a **Skill** of git **Source** `pl` with `subdirectory = "plugins/chisel"` is that folder itself
- **THEN** `cp/tdd`'s `upstream` is `pstack/skills/tdd`, and the other's is `plugins/chisel`

#### Scenario: Same lock on another machine

- **WHEN** two users with different home folders run `resolve` on the same project **Package**, whose **Sources** are
  git **Sources**, path **Sources** inside the project, and a path **Source** with `path = "~/skills"`, each user's
  holding the same skills
- **THEN** both locks are byte for byte equal

#### Scenario: Patches recorded

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/b.patch", "patches/a.patch"]`
- **THEN** the lock's entry for `mp/tdd` holds `patches = ["patches/b.patch", "patches/a.patch"]`, and entries of
  unpatched **Skills** hold no `patches`

#### Scenario: Patch changes the hash

- **WHEN** `resolve` runs, then a patch to `mp/tdd` is declared and it runs again
- **THEN** the hash of `mp/tdd` differs between the two locks, and its `upstream` does not

#### Scenario: Resolve and deploy agree with patches

- **WHEN** the user runs `resolve`, saves the lock, then runs `deploy --no-apm-install`, with patches declared
- **THEN** both locks are byte for byte equal

## MODIFIED Requirements

### Requirement: Resolve command

`skill-graft resolve` SHALL compute the **Hull** from `skill-graft.toml`, vendor it into `.apm/skills/` as `deploy`
does, write `skill-graft.lock`, print the tree to standard output and the warnings to standard error, and exit 0. The
**Vendored copies** and the lock SHALL be written together: on any failure, or an interrupt, both keep their bytes. It
SHALL NOT write `skill-graft.toml` or run `apm`. Like `deploy`, it SHALL fail on any git **Source** without `ref`.

#### Scenario: Resolve succeeds

- **WHEN** the user runs `skill-graft resolve` and every **Reference** resolves
- **THEN** it exits 0, `skill-graft.lock` exists, `.apm/skills/` holds one folder per **Hull** **Skill**, and
  `skill-graft.toml` is unchanged

#### Scenario: Resolution error

- **WHEN** a **Reference** matches several other **Sources** and no **Bind**
- **THEN** `resolve` exits non-zero and leaves any existing `skill-graft.lock` and `.apm/skills/` unchanged

#### Scenario: Lock write fails

- **WHEN** vendoring succeeded and writing `skill-graft.lock` fails
- **THEN** `resolve` exits 1 naming the error, and `.apm/skills/` and the lock are byte for byte as before

#### Scenario: First resolve, lock write fails

- **WHEN** the **Package** holds no `.apm/skills/` and no lock, and writing `skill-graft.lock` fails during `resolve`
- **THEN** `resolve` exits 1, and the **Package** holds no `.apm/skills/`, no lock and no `.gitattributes`

### Requirement: Tree output

`resolve` SHALL print the **Hull** in the style of `cargo tree`: each **Entry** at the top level in TOML order, expanded
there; under each **Skill**, one line per edge naming the **Skill** and the **Reference** as written upstream (`/name`,
`Skill(name)`, `` `name` `` or `name` plus `prose`, plus `bind` when a **Bind** decided it). A renamed **Skill** SHALL
be named `<skill id> as <deployed name>` on every line, and a patched one SHALL be followed by `(patched)` on every
line. A `prose` edge SHALL have a line only when vendoring rewrites it: its target's **Deployed name** differs from the
name written. A **Skill** SHALL be expanded once, at its first depth-first line; its later lines, and any nested line
for an **Entry**, SHALL end in `(*)` and not expand.

#### Scenario: Tree

- **WHEN** `mp/tdd` calls `/grilling`, `/notes` and `Skill(x)` (bound to `own/x`), and `mp/grilling` calls `/notes` and
  `/tdd`

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

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, `[patches]` names `mp/tdd` and `mp/grilling`, and `[rename]` has
  `"mp/grilling" = "mp-grilling"`

- **THEN** `resolve` prints

  ```text
  mp/tdd (patched)
  └── mp/grilling as mp-grilling (patched) (/grilling)
  ```

#### Scenario: Bound prose shown

- **WHEN** **Entry** `mp/tdd` calls `/notes` and mentions `` `notes` ``, `[bind]` has `"mp/notes" = "own/grill"`, and no
  rename names `own/grill`

- **THEN** `resolve` prints

  ```text
  mp/tdd
  ├── own/grill (/notes, bind)
  └── own/grill (`notes`, prose, bind) (*)
  ```

### Requirement: Lock records renames and suggestions

The lock SHALL record each renamed **Hull** **Skill**'s `deployed` name, and each suggested **Skill** with the **Skill
IDs** mentioning it, sorted. Each hash SHALL cover the folder as vendored, after renaming and rewriting, so `resolve`
and `deploy` write the same lock for the same input.

#### Scenario: Renamed skill

- **WHEN** `[rename]` has `"mp/grilling" = "mp-grilling"`
- **THEN** the lock's entry for `mp/grilling` holds `deployed = "mp-grilling"`, and entries of unrenamed **Skills** hold
  no `deployed`

#### Scenario: Suggestion recorded

- **WHEN** `mp/tdd` and `mp/grilling` mention `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** the lock holds one suggestion `mp/diagnosing-bugs` from `mp/grilling` and `mp/tdd`

#### Scenario: Rename changes the hash

- **WHEN** `resolve` runs, then `[rename]` gets `"mp/grilling" = "mp-grilling"` and it runs again, `mp/tdd` calling
  `/grilling`
- **THEN** the hashes of `mp/grilling` and `mp/tdd` differ between the two locks

#### Scenario: Resolve and build agree

- **WHEN** the user runs `resolve`, saves the lock, then runs `deploy --no-apm-install`, with renames declared
- **THEN** both locks are byte for byte equal

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to accept it
(`skill-graft add <skill id>`, named in the header), sorted, on standard output. `deploy` and `update` SHALL NOT print
them, but when there are any SHALL print one line on standard error,
`skill-graft: <n> prose suggestion(s): run skill-graft resolve`; `update` counts those of the new tips, and after
`--dry-run`, whose tips `resolve` cannot see yet, prints
`skill-graft: <n> prose suggestion(s) at the new tips: update, then run skill-graft resolve` instead, unless it moves no
`ref`: `resolve` then sees the same tips, and the line is `update`'s. `deploy --into` SHALL print no such line:
`resolve` would rewrite the **Package**'s lock, and the lock in the `--into` folder lists the suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a header naming `skill-graft add`, then a line naming `mp/diagnosing-bugs`
  and `mp/tdd`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone, and `deploy` prints no suggestion line

#### Scenario: Build announces suggestions

- **WHEN** `mp` has `diagnosing-bugs` and `notes`, **Entry** `mp/tdd` mentions `diagnosing-bugs` and `` `notes` `` but
  calls neither, and the user runs `deploy`
- **THEN** stderr holds `skill-graft: 2 prose suggestion(s): run skill-graft resolve`, and stdout no suggestion block

#### Scenario: Build into a folder announces none

- **WHEN** **Entry** `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, and the user runs `deploy --into <dir>`
- **THEN** stderr holds no `prose suggestion(s)` line, and `<dir>/skill-graft.lock` lists `mp/diagnosing-bugs`

#### Scenario: Update announces suggestions

- **WHEN** at the new tip `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, and the user runs `update`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s): run skill-graft resolve`

#### Scenario: Dry run announces suggestions

- **WHEN** the same, with `update --dry-run`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s) at the new tips: update, then run skill-graft resolve`

#### Scenario: Dry run moving no ref announces suggestions

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, `mp`'s tip is its `ref`, and the user runs
  `update --dry-run`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s): run skill-graft resolve`

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
  git **Sources** and path **Sources** inside the project
- **THEN** both locks are byte for byte equal

#### Scenario: Patches recorded

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/b.patch", "patches/a.patch"]`
- **THEN** the lock's entry for `mp/tdd` holds `patches = ["patches/b.patch", "patches/a.patch"]`, and entries of
  unpatched **Skills** hold no `patches`

#### Scenario: Patch changes the hash

- **WHEN** `resolve` runs, then a patch to `mp/tdd` is declared and it runs again
- **THEN** the hash of `mp/tdd` differs between the two locks, and its `upstream` does not

#### Scenario: Resolve and build agree with patches

- **WHEN** the user runs `resolve`, saves the lock, then runs `deploy --no-apm-install`, with patches declared
- **THEN** both locks are byte for byte equal

### Requirement: Resolve dry run and diff

`resolve --dry-run` and `resolve --diff-file <file>` SHALL behave as the editing commands' `--dry-run` and `--diff-file`
do, the **Hull diff** that of the **Vendored copies** against the **Hull** of `skill-graft.toml` as it stands, and the
hint `review: skill-graft resolve --dry-run --diff-file <file>`. Its dry run SHALL say
`dry run: skill-graft.lock and .apm/skills/ not written`. Its file's header's second line SHALL say it compares the
**Vendored copies** against what `skill-graft.toml` as it stands would vendor.

#### Scenario: A ref moved by hand

- **WHEN** the user set `sources.mp.ref` to B by hand, the lock records A, `mp/tdd` changed between them, and the user
  runs `resolve --dry-run --diff-file review.diff`
- **THEN** `mp/tdd`'s source line in `review.diff` names `mp`, A and B

#### Scenario: A patch written by hand

- **WHEN** the user added a **Patch** of `mp/tdd` to `[patches]` by hand and runs
  `resolve --dry-run --diff-file review.diff`
- **THEN** it prints `~ mp/tdd` naming each file the **Patch** changes, `review.diff` holds that text as deployed, and
  `skill-graft.lock` and `.apm/skills/` are unchanged

#### Scenario: Nothing changed

- **WHEN** nothing changed since the lock was written and the user runs `resolve --dry-run`
- **THEN** it prints `hull unchanged`, then its `dry run:` line, and no `review:` line

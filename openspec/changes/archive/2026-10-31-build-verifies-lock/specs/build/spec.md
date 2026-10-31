## ADDED Requirements

### Requirement: Build deploys the lock

`build` SHALL resolve the **Hull** as `resolve` does and deploy it only if it is the **Hull** `skill-graft.lock`
records, but for path **Source** text and folders as "Changed path Source deployed" says. Otherwise, and when the lock
is missing, cannot be read or is of another `version`, `build` SHALL exit 1 writing nothing and running no `apm`, naming
each **Skill** that differs, or what else does, and `skill-graft resolve` to accept the change.

#### Scenario: Nothing changed

- **WHEN** the user runs `resolve`, then `build`
- **THEN** `build` exits 0, and `skill-graft.lock` keeps its bytes

#### Scenario: Config edited by hand

- **WHEN** after `resolve` the user adds `mp/notes` to `entries` by hand and runs `build`
- **THEN** `build` exits 1 saying the **Hull** differs from `skill-graft.lock` and naming `skill-graft resolve`,
  `.apm/skills/`, the lock and APM are untouched, and no `.apm/skills.new/` is left

#### Scenario: Patch edited by hand

- **WHEN** after `resolve` the user edits a **Patch** of `mp/tdd` and runs `build`
- **THEN** `build` exits 1 naming `mp/tdd` as differing from `skill-graft.lock`, and naming `skill-graft resolve`

#### Scenario: Cache export edited

- **WHEN** after `resolve` a file of `mp/tdd`'s **Upstream** folder in the cache is edited and the user runs `build`
- **THEN** `build` exits 1 naming `mp/tdd`

#### Scenario: Accepted with resolve

- **WHEN** `build` refused a hand edit to the config, and the user runs `resolve`, then `build`
- **THEN** `build` exits 0 and deploys the edited config's **Hull**

#### Scenario: No lock

- **WHEN** the **Package** has no `skill-graft.lock`, as after `init`, and the user runs `build`
- **THEN** `build` exits 1 naming `skill-graft resolve`, and writes nothing

#### Scenario: Lock of another version

- **WHEN** `skill-graft.lock` records `version = 2` and the user runs `build`
- **THEN** `build` exits 1 naming `skill-graft resolve`, and writes nothing

#### Scenario: Vendoring fails

- **WHEN** after `resolve` a path **Source**'s **Skill** changed, and a copy fails during `build`
- **THEN** `build` exits non-zero naming the file, and `skill-graft.lock` and `.apm/skills/` are byte for byte as before

### Requirement: Changed path Source deployed

When the only differences from the lock are the text of **Skills** of path **Sources** that have no **Patches** and the
folders path **Sources** are recorded at, `build` SHALL vendor and deploy them, write the new hashes and folders into
`skill-graft.lock`, and once it is written print a notice naming each such **Skill**. Any change to the **Hull**'s shape
SHALL be refused as "Build deploys the lock" says, whatever **Source** caused it, and so SHALL a changed path **Source**
**Skill** with **Patches**.

#### Scenario: Own skill edited

- **WHEN** after `resolve` the user edits the text of `own/chisel`, in a path **Source**, and runs `build`
- **THEN** a notice names `own/chisel`, `.apm/skills/chisel/` holds the new text, the lock records its new hash, and
  `build` exits 0

#### Scenario: No notice when the lock write fails

- **WHEN** after `resolve` the user edits the text of `own/chisel`, and writing `skill-graft.lock` fails during `build`
- **THEN** `build` exits 1 naming the error, prints no notice naming `own/chisel`, and the lock and `.apm/skills/` are
  byte for byte as before

#### Scenario: Path source elsewhere on another machine

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"`, the committed lock records another machine's folder
  for `own`, and the user runs `build`
- **THEN** `build` exits 0, and the lock records this machine's folder for `own`

#### Scenario: Patched own skill

- **WHEN** after `resolve` the user edits a **Patch** of `own/chisel`, in a path **Source**, by hand and runs `build`
- **THEN** `build` exits 1 naming `own/chisel` and `skill-graft resolve`, and writes nothing

#### Scenario: Own skill reaches a new skill

- **WHEN** after `resolve` the user adds a call to `/grilling` to `own/chisel`, `mp/grilling` is not in the **Hull**,
  and the user runs `build`
- **THEN** `build` exits 1 naming `skill-graft resolve`, and writes nothing

### Requirement: Vendored copies match the lock

Every command that vendors (`build`, `resolve`, `update`, `add`, `remove`, `rename`, `bind`, `unbind`) SHALL first check
`.apm/skills/` against `skill-graft.lock`: a **Vendored copy** whose hash differs from the lock's, a folder the lock
lists no **Skill** under, and a file directly in `.apm/skills/`, SHALL be an error naming each, saying to move the edit
into a **Patch** or delete it, and the command SHALL then write nothing. A missing, unreadable or other-`version` lock
beside a non-empty `.apm/skills/` SHALL be an error saying the copies cannot be checked and to delete `.apm/skills/` and
run `skill-graft resolve`. A missing **Vendored copy** the lock lists SHALL be vendored again.

#### Scenario: Copy edited

- **WHEN** after `resolve` the user edits `.apm/skills/tdd/SKILL.md` and runs `build`
- **THEN** `build` exits 1 naming `.apm/skills/tdd`, a **Patch** and deleting the folder, and `.apm/skills/tdd/SKILL.md`
  keeps the edit

#### Scenario: Edited copy before an edit command

- **WHEN** `.apm/skills/tdd/SKILL.md` was edited and the user runs `skill-graft add mp/notes`
- **THEN** `add` exits 1 naming `.apm/skills/tdd`, and `skill-graft.toml`, the lock and `.apm/skills/` keep their bytes

#### Scenario: Folder added by hand

- **WHEN** the user adds `.apm/skills/mine/SKILL.md` and runs `build`
- **THEN** `build` exits 1 naming `.apm/skills/mine`, and `.apm/skills/mine/` is still there

#### Scenario: Copy deleted

- **WHEN** the user deletes `.apm/skills/tdd/` and runs `build`
- **THEN** `.apm/skills/tdd/` is vendored again and `build` exits 0

#### Scenario: Copies without a lock

- **WHEN** `.apm/skills/` holds `tdd/`, the **Package** has no `skill-graft.lock`, and the user runs `resolve`
- **THEN** `resolve` exits 1 saying `.apm/skills/` cannot be checked, to delete it and run `skill-graft resolve`, and
  writes nothing

#### Scenario: Lock unreadable

- **WHEN** `skill-graft.lock` is not valid TOML, or records `version = 2`, and the user runs `resolve`
- **THEN** `resolve` exits 1 saying `.apm/skills/` cannot be checked, not that a copy was edited

#### Scenario: File at the top

- **WHEN** the user adds `.apm/skills/README.md` and runs `resolve`
- **THEN** `resolve` exits 1 naming `.apm/skills/README.md`, and the file is still there

#### Scenario: Killed before the lock was written

- **WHEN** a `resolve` that changed `mp/tdd` was killed after swapping in the new **Vendored copies** and before writing
  `skill-graft.lock`, and the user runs `build`
- **THEN** `build` reports no edited copy, and `.apm/skills/tdd/` holds `mp/tdd` as the lock records it

#### Scenario: Killed after the lock was written

- **WHEN** a `resolve` that changed `mp/tdd` was killed after writing `skill-graft.lock` and before removing the
  previous copies, and the user runs `build`
- **THEN** `build` reports no edited copy, `.apm/skills/tdd/` holds `mp/tdd` as the new lock records it, and no previous
  copies are left

#### Scenario: Killed after the lock was written, skills only added

- **WHEN** `skill-graft add mp/notes` was killed after writing `skill-graft.lock` and before removing the previous
  copies, and the user runs `build`
- **THEN** `.apm/skills/notes/` holds `mp/notes`, no previous copies are left, and `build` exits 0

#### Scenario: Refused build leaves a killed run as it is

- **WHEN** a killed `resolve` left `.apm/skills.old/` beside `.apm/skills/`, and the user runs `build` after editing the
  config by hand
- **THEN** `build` exits 1 naming `skill-graft resolve`, and `.apm/skills/` and `.apm/skills.old/` are as before

#### Scenario: Stray file in a copy

- **WHEN** a file manager added `.apm/skills/tdd/.DS_Store` and the user runs `build`
- **THEN** `build` exits 1 naming `.apm/skills/tdd` as differing from the lock

### Requirement: Vendored copies keep their bytes in git

Every command that vendors SHALL write `.apm/skill-graft/.gitattributes` holding `/.apm/skills/** -text` and
`/patches/** -text` when the **Package** has none, together with the lock, so that git stores and checks out the
**Vendored copies** and **Patches** byte for byte. A `.gitattributes` already there SHALL be left as it is.
`build --into` SHALL write none.

#### Scenario: Attributes written

- **WHEN** the **Package** has no `.gitattributes` and the user runs `resolve`
- **THEN** `.apm/skill-graft/.gitattributes` holds `/.apm/skills/** -text` and `/patches/** -text`

#### Scenario: Own attributes kept

- **WHEN** the **Package** holds a `.gitattributes` the user wrote and the user runs `resolve`
- **THEN** it keeps its bytes

#### Scenario: None into a folder

- **WHEN** the **Package** has no `.gitattributes` and the user runs `build --into <dir>`
- **THEN** neither the **Package** nor `<dir>` holds a `.gitattributes`

#### Scenario: Checkout converting line endings

- **WHEN** a project's committed **Package** holds `.gitattributes` and its copies, and a teammate with
  `core.autocrlf=true` clones it and runs `build`
- **THEN** no copy is reported as differing from the lock

## MODIFIED Requirements

### Requirement: Build into a folder

`build --into <dir>` SHALL resolve and vendor as `build` does, but into `<dir>/.apm/skills/` instead of the
**Package**'s `.apm/skills/`, and write the lock to `<dir>/skill-graft.lock` instead of the **Package**'s. It SHALL
check the **Hull** against the **Package**'s lock as "Build deploys the lock" says, and has no **Vendored copies** to
check. It SHALL NOT run `apm`, read the scope's `apm.yml`, or create, change or delete anything in the **Package**. The
cache is written as by any `build`. A relative `<dir>` is relative to the working folder.

#### Scenario: Throwaway build

- **WHEN** the user runs `skill-graft build --into <dir>` and `<dir>` is an empty folder
- **THEN** `<dir>/.apm/skills/` holds one folder per **Hull** **Skill**, named after its **Deployed name**,
  `<dir>/skill-graft.lock` records the **Hull**, `apm` is not run, and `build` exits 0

#### Scenario: Package untouched

- **WHEN** an earlier `build` vendored the **Package**, a path **Source**'s **Skill** changed since, and the user runs
  `build --into <dir>`
- **THEN** the **Package**'s `.apm/skills/`, `skill-graft.lock` and `skill-graft.toml` are byte for byte as before, and
  `<dir>` holds the changed **Skill**

#### Scenario: Config edited by hand

- **WHEN** after `resolve` the user adds an **Entry** to `entries` by hand and runs `build --into <dir>`
- **THEN** `build` exits 1 naming `skill-graft resolve`, and `<dir>` is empty

#### Scenario: Package never built

- **WHEN** the **Package** holds no `.apm/skills/` and no `skill-graft.lock`, and the user runs `build --into <dir>`
- **THEN** `build` exits 1 naming `skill-graft resolve`, the **Package** still holds neither, and `<dir>` is empty

#### Scenario: Uncached ref

- **WHEN** a git **Source**'s `ref` is not in the cache and the user runs `build --into <dir>`
- **THEN** the commit is fetched into the cache and vendored into `<dir>`

#### Scenario: Vendoring into the folder fails

- **WHEN** a copy fails during `build --into <dir>`
- **THEN** `build` exits non-zero naming the file, and `<dir>` is empty

#### Scenario: Lock write fails

- **WHEN** vendoring into `<dir>` succeeded and writing `<dir>/skill-graft.lock` fails
- **THEN** `build` exits non-zero, and `<dir>` is empty

#### Scenario: Interrupted

- **WHEN** the user interrupts `build --into <dir>` (Ctrl-C) while it vendors
- **THEN** `<dir>` is empty

#### Scenario: Foreign file kept

- **WHEN** another process writes `<dir>/.apm/x` while `build --into <dir>` fetches, and vendoring then fails
- **THEN** `<dir>/.apm/x` is still there, and nothing `build` wrote is

#### Scenario: Temporary folder inside it

- **WHEN** `TMPDIR` is `<dir>` and vendoring fails
- **THEN** `build` exits non-zero, and `<dir>` is empty

## REMOVED Requirements

### Requirement: Build resolves first

**Reason**: `build` no longer accepts a changed **Hull**: it deploys what the lock records ("Build deploys the lock"),
and the lock and the **Vendored copies** are written together by every command that writes the lock ("Resolve command",
and `edit`'s and `update`'s "Resolve before writing"). Its warnings still come last, as "Warnings come last" says.

**Migration**: After editing `skill-graft.toml` or a **Patch** by hand, run `skill-graft resolve`, then `build`.

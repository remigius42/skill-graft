# build Specification

## Purpose

Vendors the **Entries** into the skill-graft APM package and deploys it through APM, failing loudly where APM would fail
quietly.

## Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Hull** **Skill**, named
after the **Skill**'s **Deployed name** and holding a copy of the **Skill**'s whole folder, renamed and rewritten as the
`renames` capability says and otherwise byte for byte. Nothing outside that folder is vendored. Folders from earlier
builds that are no longer in the **Hull** SHALL be removed. The folder SHALL be replaced only once every copy succeeded;
a failed copy SHALL leave it as it was. `build --into` vendors into another folder instead, as "Build into a folder"
says.

#### Scenario: Whole folder copied

- **WHEN** **Entry** `own/chisel` is a folder holding `SKILL.md` and `refs/notes.md`
- **THEN** `.apm/skills/chisel/` holds `SKILL.md` and `refs/notes.md`, byte for byte

#### Scenario: Referenced skill vendored

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, and `mp` has `grilling`
- **THEN** `.apm/skills/` holds `tdd/` and `grilling/`

#### Scenario: Renamed skill vendored

- **WHEN** **Entry** `mp/tdd` is renamed to `mp-tdd`
- **THEN** `.apm/skills/` holds `mp-tdd/` and no `tdd/`

#### Scenario: Removed entry

- **WHEN** a previous build vendored `chisel` and `chisel` is no longer in the **Hull**
- **THEN** `.apm/skills/chisel/` no longer exists after `build`

#### Scenario: Copy fails

- **WHEN** a previous build vendored `chisel`, and a **Hull** **Skill**'s folder holds a file the user cannot read
- **THEN** `build` exits non-zero naming the file, and `.apm/skills/` still holds the previous `chisel`

### Requirement: Symlinks stay within the skill

A symlink in a **Hull** **Skill**'s folder SHALL lead to an existing regular file inside that folder, and SHALL be
vendored as a copy of that file. A symlink leading outside the folder, to a missing file, to a FIFO or device, or to any
folder (which could form a cycle), SHALL be an error naming the link, and `build` SHALL then write nothing. Symlinks
under `.git`, which is never vendored, are not checked.

#### Scenario: Symlink leaving the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file or folder outside it, or to a folder inside it
- **THEN** `build` exits non-zero naming the symlink and writes nothing

#### Scenario: Symlink loop

- **WHEN** a **Hull** **Skill**'s folder holds a symlink that points to itself
- **THEN** `build` exits non-zero naming the symlink, on every supported Python version

#### Scenario: Symlink within the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file inside it
- **THEN** the vendored copy holds that file's content as a regular file

### Requirement: Deploy through APM

After vendoring, `build` without `--no-install` or `--into` SHALL run
`apm install -g <absolute path of ~/.apm/skill-graft>`, which also registers the package, and succeed only if APM exits
0 and `~/.apm/apm.yml` lists the package: as `- x` or `- path: x`, with `~` or an absolute path, compared resolved. In
project scope it SHALL instead run `apm install ./.apm/skill-graft` in the project root and check the project root's
`apm.yml`, where a relative path is relative to the project root. APM's output SHALL reach the user.

#### Scenario: APM succeeds

- **WHEN** APM exits 0 and `~/.apm/apm.yml` lists the package
- **THEN** `build` exits 0

#### Scenario: Registration removed by hand

- **WHEN** the user deleted the package's line from `~/.apm/apm.yml` and runs `build`
- **THEN** APM re-adds it and `build` exits 0

#### Scenario: Symlinked home

- **WHEN** `HOME` is a symlink and `~/.apm/apm.yml` lists the package by its resolved path
- **THEN** `build` treats the package as registered

#### Scenario: APM exits non-zero

- **WHEN** `apm install -g` exits non-zero
- **THEN** `build` exits non-zero reporting APM's exit code

#### Scenario: Package not registered

- **WHEN** APM exits 0 but `~/.apm/apm.yml` is missing or does not list the package
- **THEN** `build` exits non-zero naming `~/.apm/apm.yml` and the expected path

#### Scenario: APM missing

- **WHEN** `apm` is not on `PATH`
- **THEN** `build` exits non-zero saying APM is not installed, after vendoring

#### Scenario: Project build from a subfolder

- **WHEN** the user runs `skill-graft build` in `~/repo/src`, `~/repo/.apm/skill-graft/` exists, and APM exits 0 leaving
  `- ./.apm/skill-graft` in `~/repo/apm.yml`
- **THEN** APM ran in `~/repo` with `install ./.apm/skill-graft` and no `-g`, and `build` exits 0

#### Scenario: Project package not registered

- **WHEN** in project scope APM exits 0 but `<project>/apm.yml` does not list the package
- **THEN** `build` exits non-zero naming `<project>/apm.yml` and the expected path

### Requirement: Build without installing

`build --no-install` SHALL vendor as above and SHALL NOT run `apm` or read the scope's `apm.yml`.

#### Scenario: No install

- **WHEN** the user runs `skill-graft build --no-install`
- **THEN** `.apm/skills/` is written, `apm` is not run, and `build` exits 0

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

### Requirement: Into lock matches an in-place lock

The lock `build --into <dir>` writes SHALL be byte for byte the lock `build` would write into the **Package** from the
same input. Paths a project-scope lock records relative to the **Package** stay relative to the **Package**, not to
`<dir>`.

#### Scenario: Same lock

- **WHEN** the user runs `build --into <dir>`, then `build --no-install` with nothing changed
- **THEN** `<dir>/skill-graft.lock` and the **Package**'s `skill-graft.lock` are byte for byte equal

#### Scenario: Project path source

- **WHEN** in project scope `[sources.own]` has `path = "../../skills"` and the user runs `build --into <dir>` with
  `<dir>` outside the project
- **THEN** `<dir>/skill-graft.lock` records `own`'s path as `../../skills`

### Requirement: Into folder is empty and apart

`<dir>` SHALL be an existing, empty folder, compared resolved. It SHALL NOT lie in a **Package** (any path through
`.apm/skill-graft`, resolved or as given with `..` normalized), in a path **Source**'s folder, or in or around the git
cache, both resolved; all three compared ignoring case. Otherwise `build` SHALL exit 1 naming `<dir>` and why, before
resolving; the **Source** check follows loading the config, the others precede it. `build` SHALL never create or delete
`<dir>` itself.

#### Scenario: Missing folder

- **WHEN** `<dir>` does not exist
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and creates nothing

#### Scenario: Not empty

- **WHEN** `<dir>` holds a file, or is a file
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and leaves it as it was

#### Scenario: Inside a package

- **WHEN** `<dir>` is an empty folder inside the **Package**, inside another `.apm/skill-graft/`, or under a path such
  as `.APM/Skill-Graft/` that differs from one only in case
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and the **Package** is unchanged

#### Scenario: Inside a source

- **WHEN** `<dir>` is an empty folder inside a path **Source**'s folder, or is that folder
- **THEN** `build --into <dir>` exits 1 naming `<dir>` and the **Source**'s alias

#### Scenario: Inside the cache

- **WHEN** `<dir>` is an empty folder inside the git cache, reached directly or through a symlinked `XDG_CACHE_HOME`
- **THEN** `build --into <dir>` exits 1 naming `<dir>`

#### Scenario: Cache inside the folder

- **WHEN** `XDG_CACHE_HOME` names a folder inside the empty `<dir>`, not yet created
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and `<dir>` stays empty

#### Scenario: Symlink to an empty folder

- **WHEN** `<dir>` is a symlink to an empty folder outside any **Package**, **Source** and the cache
- **THEN** `build --into <dir>` vendors into the folder it points to and exits 0

### Requirement: Into never installs

`--into` SHALL imply not running APM, so `--into` together with `--no-install` SHALL be a usage error (exit 2), as SHALL
`--into` without a value or with an empty one. All are reported before the **Package** is looked for.

#### Scenario: With no-install

- **WHEN** the user runs `skill-graft build --into <dir> --no-install`
- **THEN** it exits 2 naming both options with `build`'s usage, and nothing is written

#### Scenario: Without a value

- **WHEN** the user runs `skill-graft build --into`
- **THEN** it exits 2 naming `--into`

#### Scenario: Empty value

- **WHEN** the user runs `skill-graft build --into ""`, as `--into "$(mktemp -d)"` does when `mktemp` fails
- **THEN** it exits 2 naming `--into`, and nothing is written, not even in the working folder

### Requirement: Into names the folder

`build --into <dir>` SHALL print `skill-graft: into: <absolute path of <dir>>` on stderr right after the
`skill-graft: package:` line, which still names the **Package**, including when the command fails after its arguments
parsed.

#### Scenario: Both lines

- **WHEN** the user runs `skill-graft build --into <dir>` in a project with a **Package**
- **THEN** stderr starts with `skill-graft: package: <project>/.apm/skill-graft`, then
  `skill-graft: into: <absolute path of <dir>>`

#### Scenario: Refused folder

- **WHEN** the user runs `skill-graft build --into <dir>` and `<dir>` is not empty
- **THEN** stderr still starts with the `package:` and `into:` lines, then the error

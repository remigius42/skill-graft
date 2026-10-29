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

### Requirement: Build resolves first

`build` SHALL resolve the **Hull** as `resolve` does before vendoring, and write `skill-graft.lock` once vendoring
succeeded, before running APM. A resolution or vendoring error SHALL leave the lock unchanged. Its warnings come last,
after APM's output, as "Warnings come last" says. `build --into` writes its lock into another folder instead, as "Build
into a folder" says.

#### Scenario: Lock written

- **WHEN** the user runs `build --no-install`
- **THEN** `skill-graft.lock` records the vendored **Hull**

#### Scenario: Vendoring fails

- **WHEN** a copy fails during `build`
- **THEN** `skill-graft.lock` is unchanged

#### Scenario: Warning does not stop build

- **WHEN** an **Entry** calls `/foo` and no **Source** has `foo`
- **THEN** `build` prints the warning and exits 0

### Requirement: Build into a folder

`build --into <dir>` SHALL resolve and vendor as `build` does, but into `<dir>/.apm/skills/` instead of the
**Package**'s `.apm/skills/`, and write the lock to `<dir>/skill-graft.lock` instead of the **Package**'s. It SHALL NOT
run `apm`, read the scope's `apm.yml`, or create, change or delete anything in the **Package**. The cache is written as
by any `build`. A relative `<dir>` is relative to the working folder.

#### Scenario: Throwaway build

- **WHEN** the user runs `skill-graft build --into <dir>` and `<dir>` is an empty folder
- **THEN** `<dir>/.apm/skills/` holds one folder per **Hull** **Skill**, named after its **Deployed name**,
  `<dir>/skill-graft.lock` records the **Hull**, `apm` is not run, and `build` exits 0

#### Scenario: Package untouched

- **WHEN** an earlier `build` vendored the **Package**, an **Upstream** **Skill** changed since, and the user runs
  `build --into <dir>`
- **THEN** the **Package**'s `.apm/skills/`, `skill-graft.lock` and `skill-graft.toml` are byte for byte as before, and
  `<dir>` holds the changed **Skill**

#### Scenario: Package never built

- **WHEN** the **Package** holds no `.apm/skills/` and no `skill-graft.lock`, and the user runs `build --into <dir>`
- **THEN** the **Package** still holds neither

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

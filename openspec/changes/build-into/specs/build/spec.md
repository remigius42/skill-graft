# Spec Delta

## ADDED Requirements

### Requirement: Build into a folder

`build --into <dir>` SHALL resolve and vendor as `build` does, but into `<dir>/.apm/skills/` instead of the
**Package**'s `.apm/skills/`, and write the lock to `<dir>/skill-graft.lock` instead of the **Package**'s. It
SHALL NOT run `apm`, read the scope's `apm.yml`, or create, change or delete anything in the **Package**. The
cache is written as by any `build`. A relative `<dir>` is relative to the working folder.

#### Scenario: Throwaway build

- **WHEN** the user runs `skill-graft build --into <dir>` and `<dir>` is an empty folder
- **THEN** `<dir>/.apm/skills/` holds one folder per **Hull** **Skill**, named after its **Deployed name**,
  `<dir>/skill-graft.lock` records the **Hull**, `apm` is not run, and `build` exits 0

#### Scenario: Package untouched

- **WHEN** an earlier `build` vendored the **Package**, an **Upstream** **Skill** changed since, and the user runs
  `build --into <dir>`
- **THEN** the **Package**'s `.apm/skills/`, `skill-graft.lock` and `skill-graft.toml` are byte for byte as
  before, and `<dir>` holds the changed **Skill**

#### Scenario: Package never built

- **WHEN** the **Package** holds no `.apm/skills/` and no `skill-graft.lock`, and the user runs
  `build --into <dir>`
- **THEN** the **Package** still holds neither

#### Scenario: Uncached ref

- **WHEN** a git **Source**'s `ref` is not in the cache and the user runs `build --into <dir>`
- **THEN** the commit is fetched into the cache and vendored into `<dir>`

#### Scenario: Vendoring fails

- **WHEN** a copy fails during `build --into <dir>`
- **THEN** `build` exits non-zero naming the file, and `<dir>` is empty

### Requirement: Into lock matches an in-place lock

The lock `build --into <dir>` writes SHALL be byte for byte the lock `build` would write into the **Package**
from the same input. Paths a project-scope lock records relative to the **Package** stay relative to the
**Package**, not to `<dir>`.

#### Scenario: Same lock

- **WHEN** the user runs `build --into <dir>`, then `build --no-install` with nothing changed
- **THEN** `<dir>/skill-graft.lock` and the **Package**'s `skill-graft.lock` are byte for byte equal

#### Scenario: Project path source

- **WHEN** in project scope `[sources.own]` has `path = "../../skills"` and the user runs `build --into <dir>`
  with `<dir>` outside the project
- **THEN** `<dir>/skill-graft.lock` records `own`'s path as `../../skills`

### Requirement: Into folder is empty and apart

`<dir>` SHALL be an existing, empty folder, compared resolved. It SHALL NOT lie in a **Package** (a path running
through `.apm/skill-graft`, as given or resolved), in or around a path **Source**'s folder, or in the git cache.
Otherwise `build` SHALL exit 1 naming `<dir>` and why, before resolving and writing anything. `build` SHALL never
create or delete `<dir>` itself.

#### Scenario: Missing folder

- **WHEN** `<dir>` does not exist
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and creates nothing

#### Scenario: Not empty

- **WHEN** `<dir>` holds a file, or is a file
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and leaves it as it was

#### Scenario: Inside a package

- **WHEN** `<dir>` is an empty folder inside the **Package**, or inside another `.apm/skill-graft/`
- **THEN** `build --into <dir>` exits 1 naming `<dir>`, and the **Package** is unchanged

#### Scenario: Inside a source

- **WHEN** `<dir>` is an empty folder inside a path **Source**'s folder, or is that folder
- **THEN** `build --into <dir>` exits 1 naming `<dir>` and the **Source**'s alias

#### Scenario: Inside the cache

- **WHEN** `<dir>` is an empty folder inside the git cache
- **THEN** `build --into <dir>` exits 1 naming `<dir>`

#### Scenario: Symlink to an empty folder

- **WHEN** `<dir>` is a symlink to an empty folder outside any **Package**, **Source** and the cache
- **THEN** `build --into <dir>` vendors into the folder it points to and exits 0

### Requirement: Into never installs

`--into` SHALL imply not running APM, so `--into` together with `--no-install` SHALL be a usage error (exit 2),
as SHALL `--into` without a value. Both are reported before the **Package** is looked for.

#### Scenario: With no-install

- **WHEN** the user runs `skill-graft build --into <dir> --no-install`
- **THEN** it exits 2 naming both options, and nothing is written

#### Scenario: Without a value

- **WHEN** the user runs `skill-graft build --into`
- **THEN** it exits 2 naming `--into`

### Requirement: Into names the folder

`build --into <dir>` SHALL print `skill-graft: into: <absolute path of <dir>>` on stderr right after the
`skill-graft: package:` line, which still names the **Package**, including when the command fails after its
arguments parsed.

#### Scenario: Both lines

- **WHEN** the user runs `skill-graft build --into <dir>` in a project with a **Package**
- **THEN** stderr starts with `skill-graft: package: <project>/.apm/skill-graft`, then
  `skill-graft: into: <absolute path of <dir>>`

#### Scenario: Refused folder

- **WHEN** the user runs `skill-graft build --into <dir>` and `<dir>` is not empty
- **THEN** stderr still starts with the `package:` and `into:` lines, then the error

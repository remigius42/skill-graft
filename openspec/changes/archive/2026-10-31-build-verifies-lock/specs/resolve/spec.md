## MODIFIED Requirements

### Requirement: Resolve command

`skill-graft resolve` SHALL compute the **Hull** from `skill-graft.toml`, vendor it into `.apm/skills/` as `build` does,
write `skill-graft.lock`, print the tree to standard output and the warnings to standard error, and exit 0. The
**Vendored copies** and the lock SHALL be written together: on any failure, or an interrupt, both keep their bytes. It
SHALL NOT write `skill-graft.toml` or run `apm`. Like `build`, it SHALL fail on any git **Source** without `ref`.

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

## REMOVED Requirements

### Requirement: The lock is output only

**Reason**: `build` and every command that vendors now read the lock: `build` deploys only what it records, and the
**Vendored copies** are checked against it (`build`'s "Build deploys the lock" and "Vendored copies match the lock").

**Migration**: Do not edit `skill-graft.lock`; run `skill-graft resolve` to rewrite it from the config. If the lock was
edited by hand, cannot be read or is of another `version`, `resolve` cannot check the **Vendored copies**: delete
`.apm/skills/`, then run `skill-graft resolve`.

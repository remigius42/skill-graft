## ADDED Requirements

### Requirement: Version

`skill-graft --version` SHALL print `skill-graft <version>` to standard output and exit 0, without reading
`skill-graft.toml`. Installed from a git repository, the version SHALL be followed by the revision asked for and the
commit installed, abbreviated to seven characters: `(<revision> @ <commit>)`, or `(<commit>)` when no revision was
asked for. Installed from anywhere else, it SHALL print the version only. The top-level help SHALL list `--version`.

#### Scenario: Release

- **WHEN** skill-graft 0.2.0 was installed from a package index, a local folder or an archive, and the user runs
  `skill-graft --version`
- **THEN** it exits 0 and prints `skill-graft 0.2.0`

#### Scenario: Git install at a branch

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft@main` at commit
  `e294a0e…`, and the user runs `skill-graft --version`
- **THEN** it prints `skill-graft 0.2.0 (main @ e294a0e)`

#### Scenario: Git install without a revision

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft` at commit `e294a0e…`,
  and the installer recorded no revision
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)`

#### Scenario: No package

- **WHEN** the user runs `skill-graft --version` in a folder with no `~/.apm/skill-graft/`
- **THEN** it exits 0 and prints the version

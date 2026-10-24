# Spec Delta

## MODIFIED Requirements

### Requirement: Version

`skill-graft --version` SHALL print `skill-graft <version>` on one line to standard output and exit 0, without
reading `skill-graft.toml`. Installed from a git repository, the version SHALL be followed by the revision asked for
and the commit installed, abbreviated to seven characters: `(<revision> @ <commit>)`, or `(<commit>)` when no revision
was asked for, the revision holds a character that is not printable, or the revision is that commit, in full or
abbreviated to seven or more characters. A commit holding a character that is not printable SHALL add nothing.
Installed from anywhere else, it SHALL print the version only.

#### Scenario: Release

- **WHEN** skill-graft 0.2.0 was installed from a package index, a local folder or an archive, and the user runs
  `skill-graft --version`
- **THEN** it exits 0 and prints `skill-graft 0.2.0`

#### Scenario: Git install without a revision

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft` at commit `e294a0e…`,
  and the installer recorded no revision
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)`

#### Scenario: Git install at a branch

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft@main` at commit
  `e294a0e…`
- **THEN** it prints `skill-graft 0.2.0 (main @ e294a0e)`

#### Scenario: Git install at a commit

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft@` followed by the full
  or a short hash of commit `e294a0e…`
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)`

#### Scenario: Revision that is not printable

- **WHEN** skill-graft 0.2.0 was installed from git at commit `e294a0e…`, and the installer recorded the revision
  `main` followed by a newline and `foo`, or one holding an escape character
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)` on one line

#### Scenario: Commit that is not printable

- **WHEN** skill-graft 0.2.0 was installed from git, and the installer recorded a commit holding an escape character
- **THEN** it prints `skill-graft 0.2.0`

#### Scenario: Other version control

- **WHEN** skill-graft 0.2.0 was installed from a Mercurial or Subversion repository
- **THEN** it prints `skill-graft 0.2.0`

#### Scenario: Broken package

- **WHEN** the nearest `.apm/skill-graft/skill-graft.toml` is not valid TOML, and the user runs `skill-graft --version`
- **THEN** it exits 0 and prints the version

#### Scenario: Listed in help

- **WHEN** the user runs `skill-graft --help`
- **THEN** it lists `--version`

## ADDED Requirements

### Requirement: Version on a damaged installation

`skill-graft --version` SHALL exit 0 whatever the installation holds. When the installer's record of where it came
from cannot be read or parsed, it SHALL print the version only. When no installed metadata names a version, or it
cannot be read, it SHALL print `skill-graft unknown`.

#### Scenario: Unreadable record

- **WHEN** skill-graft 0.2.0 is installed, and its `direct_url.json` is a symlink loop, sits on a failing disk, or holds
  JSON nested too deeply to parse
- **THEN** `skill-graft --version` exits 0 and prints `skill-graft 0.2.0`

#### Scenario: Not installed

- **WHEN** skill-graft runs from its source folder without installed metadata, and the user runs
  `skill-graft --version`
- **THEN** it exits 0 and prints `skill-graft unknown`

#### Scenario: Unreadable metadata

- **WHEN** skill-graft's installed metadata cannot be read, or names no version
- **THEN** `skill-graft --version` exits 0 and prints `skill-graft unknown`

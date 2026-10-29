# Spec Delta

## ADDED Requirements

### Requirement: Supported platforms

skill-graft SHALL run on Linux and macOS, and on Windows through WSL, which is Linux. On native Windows, every command
line SHALL print one error line saying Windows is unsupported and to run it in WSL, to standard error, and exit 1, with
no traceback and nothing on standard output. This takes precedence over every other requirement of this capability,
including the exit codes of help, `--version` and usage errors.

#### Scenario: Native Windows

- **WHEN** the user runs `skill-graft resolve` on native Windows
- **THEN** standard output is empty, standard error holds only the error line naming WSL, no traceback, and the command
  exits 1

#### Scenario: Help and version on native Windows

- **WHEN** the user runs `skill-graft help`, `skill-graft --help` or `skill-graft --version` on native Windows
- **THEN** standard output is empty, standard error holds only the error line naming WSL, and the command exits 1, not 0

#### Scenario: Usage errors on native Windows

- **WHEN** the user runs `skill-graft`, `skill-graft explain` or `skill-graft --bogus` on native Windows
- **THEN** standard output is empty, standard error holds only the error line naming WSL, and the command exits 1, not 2

#### Scenario: Linux and macOS

- **WHEN** the user runs `skill-graft --version` on Linux or macOS
- **THEN** it prints the version and exits 0

# cli

## ADDED Requirements

### Requirement: Closed standard output

When the reader of standard output closes it before a command, `help`, `--version` and `--help` included, has written
everything, the command SHALL still print its warnings on standard error, then its error line. A command that failed for
its own reason SHALL report that error; one that did not SHALL report the closed output. Either SHALL exit 1, and Python
SHALL print nothing of its own. Started with standard output closed, a command SHALL print its warnings and exit as it
would with standard output open.

#### Scenario: Warnings survive

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and the user runs `skill-graft tree` into a pipe whose
  reader has closed it
- **THEN** the `/foo` warning is printed, then the error line naming the broken pipe, and the command exits 1

#### Scenario: The command's own error wins

- **WHEN** an **Entry**'s **Skill** holds hidden characters and the user runs `skill-graft tree` into a pipe whose
  reader has closed it
- **THEN** the hidden-characters error is printed, not the broken pipe, and the command exits 1

#### Scenario: No Python output

- **WHEN** the user runs `skill-graft tree` into a pipe whose reader has closed it
- **THEN** standard error holds no `Exception ignored` line, and the exit code is 1, not 120

#### Scenario: Help, version and argparse's help

- **WHEN** the user runs `skill-graft help`, `skill-graft --version`, `skill-graft --help`, or
  `skill-graft tree --help`, into a pipe whose reader has closed it
- **THEN** the error line naming the broken pipe is printed, with no `Exception ignored` line, and the command exits 1

#### Scenario: Closed from the start

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and the user runs `skill-graft tree >&-`
- **THEN** the `/foo` warning is printed, no traceback, and the command exits 0

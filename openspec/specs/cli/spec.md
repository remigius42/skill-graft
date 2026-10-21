# cli Specification

## Purpose

How the user learns and invokes the `skill-graft` commands: help for each command, the `help` command, and what
a mistyped command line does.

## Requirements

### Requirement: Help on every command

`skill-graft -h`, `skill-graft --help` and `-h`/`--help` after any command SHALL print that level's usage, a
description in the glossary's terms, and each argument and option with its meaning, to standard output, and
exit 0 without reading `skill-graft.toml`. The top level SHALL list every command with a one-line summary.

#### Scenario: Top-level help

- **WHEN** the user runs `skill-graft --help`
- **THEN** it exits 0 and lists `init`, `resolve`, `build`, `update`, `why`, `tree`, `add`, `remove`, `rename`,
  `bind`, `unbind` and `help`, each with a summary

#### Scenario: Command help

- **WHEN** the user runs `skill-graft add --help` in a folder with no `~/.apm/skill-graft/`
- **THEN** it exits 0 and describes `<skill-id>` as a **Skill ID** and what `add` writes

### Requirement: Help command

`skill-graft help` SHALL print what `skill-graft --help` prints; `skill-graft help <command>` SHALL print what
`skill-graft <command> --help` prints. `help` with an unknown command SHALL be a usage error.

#### Scenario: Same text

- **WHEN** the user runs `skill-graft help tree` and `skill-graft tree --help`
- **THEN** both exit 0 with the same output

#### Scenario: Unknown topic

- **WHEN** the user runs `skill-graft help nope`
- **THEN** it exits 2, naming `nope` and listing the commands on standard error

### Requirement: Usage errors

No command, an unknown command, a missing or extra argument, or an unknown option SHALL print the usage and the error to
standard error and exit 2, distinct from the exit 1 of a failing command. An argument of the right count but an invalid
value, such as a malformed **Skill ID**, SHALL be a failing command (exit 1). No command and an unknown command SHALL
also list the commands.

#### Scenario: Unknown command

- **WHEN** the user runs `skill-graft explain`
- **THEN** it exits 2, and standard error names `explain` and lists the commands

#### Scenario: No command

- **WHEN** the user runs `skill-graft`
- **THEN** it exits 2, and standard error lists the commands

#### Scenario: Missing argument

- **WHEN** the user runs `skill-graft rename mp/tdd`
- **THEN** it exits 2, naming the missing `name`

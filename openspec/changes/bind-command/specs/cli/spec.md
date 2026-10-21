## MODIFIED Requirements

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

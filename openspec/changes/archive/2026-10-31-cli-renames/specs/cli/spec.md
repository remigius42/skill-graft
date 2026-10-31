## MODIFIED Requirements

### Requirement: Help on every command

`skill-graft -h`, `skill-graft --help` and `-h`/`--help` after any command SHALL print that level's usage, a description
in the glossary's terms, and each argument and option with its meaning, to standard output, and exit 0 without reading
`skill-graft.toml`. The top level SHALL list every command with a one-line summary.

#### Scenario: Top-level help

- **WHEN** the user runs `skill-graft --help`
- **THEN** it exits 0 and lists `init`, `resolve`, `deploy`, `update`, `why`, `tree`, `add`, `remove`, `rename`, `bind`,
  `unbind` and `help`, each with a summary

#### Scenario: Command help

- **WHEN** the user runs `skill-graft add --help` in a folder with no `~/.apm/skill-graft/`
- **THEN** it exits 0 and describes `<skill-id>` as a **Skill ID** and what `add` writes

### Requirement: Warnings come last

Every command SHALL print its warnings, those about `skill-graft.toml` and those about the **Hull**, on standard error
after everything else it prints, its notices and APM's output included, and only its error line, if it fails, after
them. A command that fails after it read the config or computed the **Hull** SHALL still print the warnings found so
far. Each warning SHALL be printed once. An edit that changes no value SHALL print none, as the edit spec has it print
only its notices.

#### Scenario: Resolve

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and the user runs `skill-graft resolve`
- **THEN** the `/foo` warning is printed after the tree and the suggestions

#### Scenario: Build

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and the user runs `skill-graft deploy`
- **THEN** the `/foo` warning is printed after APM's output

#### Scenario: Update

- **WHEN** an **Entry** calls `/foo` at the new tip, no **Source** has `foo`, and the user runs
  `skill-graft update --dry-run`
- **THEN** the `/foo` warning is printed after the **Hull diff** and the `dry run:` line

#### Scenario: Edit with a notice

- **WHEN** `mp/tdd` reaches `mp/grilling`, `mp/tdd` calls `/foo`, no **Source** has `foo`, and the user runs
  `skill-graft add mp/grilling`
- **THEN** the `/foo` warning is printed after the tree and after the notice that `mp/grilling` was already in the
  **Hull**

#### Scenario: Config warning

- **WHEN** a path **Source** lies inside a folder APM deploys to and the user runs `skill-graft resolve`
- **THEN** the warning naming it is printed after the tree, not before

#### Scenario: Edit fails before resolving

- **WHEN** a path **Source** `own` lies inside a folder APM deploys to and the user runs `skill-graft unbind own/x`,
  which is not bound
- **THEN** the warning naming `own` is printed, then the error, and the command exits 1

#### Scenario: Failing command

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and `skill-graft.lock` cannot be written during
  `skill-graft resolve`
- **THEN** the `/foo` warning is printed, then the error line, and the command exits 1

#### Scenario: Edit that changes nothing

- **WHEN** a path **Source** `own` lies inside a folder APM deploys to, `own/chisel` is an **Entry**, and the user runs
  `skill-graft add own/chisel`
- **THEN** only the notice that `own/chisel` is already an entry is printed, and the command exits 0

## ADDED Requirements

### Requirement: Options spelled in full

Every option SHALL be given by its full name: a prefix of an option, even one only it starts with, SHALL be a usage
error (exit 2) naming it, reported before the **Package** is looked for.

#### Scenario: Prefix of an option

- **WHEN** the user runs `skill-graft update --dry`
- **THEN** it exits 2 naming `--dry`, and nothing is read or written

#### Scenario: Full name

- **WHEN** the user runs `skill-graft update --dry-run`
- **THEN** it runs as a dry run

### Requirement: Former names refused

`build`, `--no-install` and `--diff`, renamed to `deploy`, `--no-apm-install` and `--diff-file`, SHALL be usage errors
(exit 2) like any unknown command or option, with no alias and no deprecation notice.

#### Scenario: Old command

- **WHEN** the user runs `skill-graft build`
- **THEN** it exits 2 naming `build` and listing `deploy` among the commands, and nothing is written

#### Scenario: Old install option

- **WHEN** the user runs `skill-graft deploy --no-install`
- **THEN** it exits 2 naming `--no-install`, and `apm` is not run

#### Scenario: Old diff option

- **WHEN** the user runs `skill-graft update --dry-run --diff review.diff`
- **THEN** it exits 2 naming `--diff`, and `review.diff` is not written

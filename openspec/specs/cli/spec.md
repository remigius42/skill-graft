# cli Specification

## Purpose

How the user learns and invokes the `skill-graft` commands: help for each command, the `help` command, and what a
mistyped command line does.

## Requirements

### Requirement: Help on every command

`skill-graft -h`, `skill-graft --help` and `-h`/`--help` after any command SHALL print that level's usage, a description
in the glossary's terms, and each argument and option with its meaning, to standard output, and exit 0 without reading
`skill-graft.toml`. The top level SHALL list every command with a one-line summary.

#### Scenario: Top-level help

- **WHEN** the user runs `skill-graft --help`
- **THEN** it exits 0 and lists `init`, `resolve`, `build`, `update`, `why`, `tree`, `add`, `remove`, `rename`, `bind`,
  `unbind` and `help`, each with a summary

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

### Requirement: Version

`skill-graft --version` SHALL print `skill-graft <version>` on one line to standard output and exit 0, without reading
`skill-graft.toml`. Installed from a git repository, the version SHALL be followed by the revision asked for and the
commit installed, abbreviated to seven characters: `(<revision> @ <commit>)`, or `(<commit>)` when no revision was asked
for, the revision is not printable ASCII without spaces, or the revision is that commit, in full or abbreviated to seven
or more characters. A commit that is not a hexadecimal hash of seven or more digits SHALL add nothing. Installed from
anywhere else, it SHALL print the version only.

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

- **WHEN** skill-graft 0.2.0 was installed from `git+https://github.com/remigius42/skill-graft@` followed by the full or
  a short hash of commit `e294a0e…`
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)`

#### Scenario: Revision that is not printable ASCII without spaces

- **WHEN** skill-graft 0.2.0 was installed from git at commit `e294a0e…`, and the installer recorded the revision `main`
  followed by a newline and `foo`, one holding an escape character, `ブランチ`, or `main @ abc1234`
- **THEN** it prints `skill-graft 0.2.0 (e294a0e)` on one line

#### Scenario: Commit that is not a hash

- **WHEN** skill-graft 0.2.0 was installed from git, and the installer recorded the commit `abc) x`, or one holding an
  escape character
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

### Requirement: Version on a damaged installation

`skill-graft --version` SHALL exit 0 whatever the installation holds. When the installer's record of where it came from
cannot be read or parsed, it SHALL print the version only. When no installed metadata is found, or it cannot be read or
decoded, or its version, stripped of surrounding whitespace, is missing or not printable ASCII without spaces, the
version SHALL read `unknown`, followed by the commit as for any version.

#### Scenario: Unreadable record

- **WHEN** skill-graft 0.2.0 is installed, and its `direct_url.json` is a symlink loop, sits on a failing disk, or holds
  JSON nested too deeply to parse
- **THEN** `skill-graft --version` exits 0 and prints `skill-graft 0.2.0`

#### Scenario: Not installed

- **WHEN** skill-graft runs from its source folder without installed metadata, and the user runs `skill-graft --version`
- **THEN** it exits 0 and prints `skill-graft unknown`

#### Scenario: Unreadable metadata

- **WHEN** skill-graft's installed metadata cannot be read, is not UTF-8, names no version, or names one holding a
  newline or a space, such as `0.2.0 (main @ abc1234)`
- **THEN** `skill-graft --version` exits 0 and prints `skill-graft unknown`

#### Scenario: Version padded with whitespace

- **WHEN** skill-graft's installed metadata names the version `0.2.0` with a space before and after it
- **THEN** `skill-graft --version` prints `skill-graft 0.2.0`

#### Scenario: Unknown version from git

- **WHEN** skill-graft's installed metadata names no version, and it was installed from git at `main`, commit `e294a0e…`
- **THEN** `skill-graft --version` prints `skill-graft unknown (main @ e294a0e)`

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

- **WHEN** an **Entry** calls `/foo`, no **Source** has `foo`, and the user runs `skill-graft build`
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

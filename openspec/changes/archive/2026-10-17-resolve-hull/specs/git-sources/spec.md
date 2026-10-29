# Spec Delta

## MODIFIED Requirements

### Requirement: Cache outside the package

Git **Sources** SHALL be cached under `$XDG_CACHE_HOME/skill-graft/`, else `~/.cache/skill-graft/`: one bare repository
per git URL, shared by every alias naming that URL and fetched at most once per command, and one checkout per commit.
Deleting the cache SHALL lose nothing: the next command that needs a **Ref** fetches it again. An interrupted clone or
checkout SHALL never be mistaken for a complete one, nor block the next run.

#### Scenario: Default location

- **WHEN** `XDG_CACHE_HOME` is unset and `build` reads a git **Source**
- **THEN** its repository and checkout are under `~/.cache/skill-graft/`, and `build` writes nothing under
  `~/.apm/skill-graft/` outside `.apm/skills/` and `skill-graft.lock`

#### Scenario: Shared URL

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL
- **THEN** the cache holds one repository for both, and a command fetches it once

#### Scenario: Cache deleted

- **WHEN** the user deletes the cache folder and runs `build`
- **THEN** `build` fetches again and vendors the same files

#### Scenario: Interrupted checkout

- **WHEN** a previous run left a partial checkout of the `ref` behind
- **THEN** the next `build` ignores it, checks the `ref` out again, and vendors every file

#### Scenario: Concurrent runs

- **WHEN** two commands export the same `ref`, or clone the same URL, at the same time
- **THEN** both succeed, and the cache holds one export or repository

#### Scenario: Interrupted clone

- **WHEN** a previous run was killed while cloning a git **Source** for the first time
- **THEN** the next `build` clones it again and succeeds

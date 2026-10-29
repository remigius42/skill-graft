## ADDED Requirements

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

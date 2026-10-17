# Spec Delta

## MODIFIED Requirements

### Requirement: Sources stay clear of the package and deploy folders

A source whose folder is inside `~/.apm/skill-graft/` or contains it SHALL be an error. A source inside or
containing an APM deploy folder (`~/.agents/skills`, `~/.claude/skills`, and the other harness skill folders)
SHALL be a warning naming the alias and the folder. In project scope the deploy folders are the user scope's
plus `.agents/skills`, `.claude/skills`, `.grok/skills` and `.kiro/skills` under the project root. Paths are
compared resolved.

#### Scenario: Source is the package

- **WHEN** `[sources.own]` has `path = "."` (the folder holding `skill-graft.toml`)
- **THEN** the command exits non-zero naming `own` and writes nothing

#### Scenario: Source is a deploy folder

- **WHEN** `[sources.own]` has `path = "~/.agents/skills"`
- **THEN** the command prints a warning naming `own` and `~/.agents/skills`, and continues

#### Scenario: Source is the project's deploy folder

- **WHEN** in project scope `[sources.own]` has `path = "../../.claude/skills"`
- **THEN** the command prints a warning naming `own` and `<project>/.claude/skills`, and continues

#### Scenario: Project source is a user deploy folder

- **WHEN** in project scope `[sources.own]` has `path = "~/.claude/skills"`
- **THEN** the command prints a warning naming `own` and `~/.claude/skills`, and continues

#### Scenario: Source contains the project package

- **WHEN** in project scope `[sources.own]` has `path = "../.."` (the project root)
- **THEN** the command exits non-zero naming `own` and writes nothing

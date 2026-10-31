## MODIFIED Requirements

### Requirement: Writing commands fail alike

`resolve`, `deploy` (with `--into` too), `update`, and the commands that edit the config SHALL fail on a **Hidden
character** as `resolve` does, writing nothing: no lock, no `.apm/skills/`, no `ref`, no config change, and no `apm`
run.

#### Scenario: Build into a folder

- **WHEN** a **Hull** **Skill** holds U+E0041 and the user runs `skill-graft deploy --into <dir>`
- **THEN** it exits 1 and `<dir>` stays empty

#### Scenario: Update to a tip holding one

- **WHEN** the tip of **Source** `mp`'s branch adds U+E0041 to a **Hull** **Skill**, and the user runs
  `skill-graft update mp`
- **THEN** it exits 1 and `mp`'s `ref` is unchanged

#### Scenario: Add a skill holding one

- **WHEN** `mp/notes` holds U+E0041 and the user runs `skill-graft add mp/notes`
- **THEN** it exits 1 and `skill-graft.toml` keeps its bytes

#### Scenario: Remove the skill holding one

- **WHEN** **Entry** `mp/notes` holds U+E0041, nothing else reaches it, and the user runs `skill-graft remove mp/notes`
- **THEN** it succeeds, as the edited config's **Hull** holds no **Hidden character**

# Spec Delta

## MODIFIED Requirements

### Requirement: Skill name

A **Skill**'s name SHALL be the `name:` value of the YAML front matter opening its `SKILL.md`, else its folder name. Its
**Skill ID** is `<source alias>/<name>`. A leading BOM, trailing whitespace on the `---` fences, surrounding quotes, and
a trailing comment (whitespace then `#`) SHALL NOT change the name.

#### Scenario: Front matter name

- **WHEN** `skills/tdd-v2/SKILL.md` opens with front matter holding `name: tdd`
- **THEN** its **Skill ID** in source `mp` is `mp/tdd`

#### Scenario: No front matter name

- **WHEN** `grilling/SKILL.md` has no front matter, or front matter without `name:`
- **THEN** its name is `grilling`

#### Scenario: Comment and quotes

- **WHEN** the front matter holds `name: "tdd" # renamed` and the file starts with a UTF-8 BOM
- **THEN** the name is `tdd`

#### Scenario: Unsupported YAML form

- **WHEN** the front matter holds `name: >-` followed by an indented value
- **THEN** a command that needs that skill exits non-zero naming the `SKILL.md`, rather than using the folder name

#### Scenario: Long run of whitespace

- **WHEN** the front matter holds `name: a`, 100 000 spaces, then `b`, and that **Skill** is an **Entry**
- **THEN** `resolve` exits non-zero within seconds, as for any name that is not one path segment

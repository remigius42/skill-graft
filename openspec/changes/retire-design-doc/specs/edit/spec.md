## MODIFIED Requirements

### Requirement: Edit reports the hull diff

An edit with `--dry-run` or `--diff-file` SHALL print, before its tree, the **Hull diff** of the **Vendored copies**
against the **Hull** it would vendor, in `update`'s form: `hull (+ added, - removed, ~ changed):`, then `+`, `-` or `~`
and the **Skill ID** per **Skill**, sorted, each changed file under a `+` or `~` line as `update` names them; or
`hull unchanged`. A plain edit SHALL print as before. A **Skill** is matched to its copy through the lock's **Skill
IDs** and **Deployed names**, and a copy read only as an entry of `.apm/skills/`, or of the `.apm/skills.old/` a killed
run left when the next writing run would keep it; one the lock records without a copy, and every **Skill** with no lock,
is `+`, and a **Skill** is `-` only when it leaves the **Hull** and had a copy. A removed **Skill**'s ID, read from the
lock, SHALL be quoted as file paths are. Without `--diff-file`, when it marks a **Skill** `+` or `~`, it SHALL print
`review: skill-graft <command> <arguments> --dry-run --diff-file <file>`, each argument quoted for a POSIX shell, right
before its `dry run:` line.

#### Scenario: Skills joining

- **WHEN** `mp/tdd` calls `/grilling`, neither is in the **Hull**, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints `+ mp/grilling` and `+ mp/tdd`, each with its files as `(new, <n> bytes)`

#### Scenario: Text changed by a bind

- **WHEN** `mp/tdd` calls `/grilling`, and the user runs `bind mp/grilling cp/grilling --dry-run`, where `cp/grilling`
  deploys as `cp-grilling`
- **THEN** it prints `+ cp/grilling`, `- mp/grilling`, and `~ mp/tdd` naming its `SKILL.md`, whose reference is
  rewritten

#### Scenario: Renamed skill

- **WHEN** `mp/tdd` is in the **Hull** and the user runs `rename mp/tdd mp-tdd --dry-run`
- **THEN** it prints `~ mp/tdd`, not a `-` and a `+`

#### Scenario: First add

- **WHEN** the **Package** holds no lock and no `.apm/skills/`, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints every **Skill** of the **Hull** as `+`

#### Scenario: Hint

- **WHEN** the user runs `add mp/tdd --dry-run` without `--diff-file`, and `mp/tdd` joins the **Hull**
- **THEN** it prints `review: skill-graft add mp/tdd --dry-run --diff-file <file>` before its `dry run:` line

#### Scenario: Nothing changed

- **WHEN** `mp/tdd` is already in the **Hull**, through another **Entry**, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints `hull unchanged` and no `review:` line

#### Scenario: Plain edit unchanged

- **WHEN** the user runs `add mp/tdd` without `--dry-run` or `--diff-file`
- **THEN** it prints what it printed before, and no **Hull diff**

#### Scenario: A lock pointing outside the copies

- **WHEN** the lock records `mp/tdd` with `deployed = "../../outside"` and no copy deployed under that name, and the
  user runs `add mp/notes --dry-run --diff-file review.diff`
- **THEN** it reads nothing outside `.apm/skills/`, and prints `mp/tdd` as `+`

#### Scenario: After a killed run

- **WHEN** a run was killed after swapping in new copies and before writing the lock, so `.apm/skills.old/` holds the
  copies the lock records, and the user runs `resolve --dry-run`
- **THEN** the **Hull diff** compares against the copies in `.apm/skills.old/`, not those in `.apm/skills/`

#### Scenario: A removed ID holding a control character

- **WHEN** the lock records a **Skill** whose ID holds a line feed and an escape character, and it leaves the **Hull**
- **THEN** its `-` line, and its `# -` line in the diff file, show the ID quoted, on one line

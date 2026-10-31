# Spec Delta

## ADDED Requirements

### Requirement: Edit dry run writes nothing

`add`, `remove`, `rename`, `bind` and `unbind` with `--dry-run` SHALL check, resolve and print as without it, exiting
with the same code, but SHALL write neither `skill-graft.toml`, `skill-graft.lock`, `.apm/skills/`, `.gitattributes`
nor the cache, nor anything outside a temporary folder it removes before exiting, except the **Deployed diff** file
`--diff` names. It SHALL say `dry run: skill-graft.toml, skill-graft.lock and .apm/skills/ not written`. An edit that
changes no value SHALL print only its notices, as without `--dry-run`.

#### Scenario: Dry run of an add

- **WHEN** the user runs `add mp/tdd --dry-run` and the edited config resolves
- **THEN** it prints the **Hull diff** and its `dry run:` line, and `skill-graft.toml`, `skill-graft.lock`,
  `.apm/skills/` and the cache folder are unchanged

#### Scenario: Dry run of a failing edit

- **WHEN** the user runs `add mp/notes --dry-run` and `mp/notes` calls `/x`, which matches several other **Sources**
  and no **Bind**
- **THEN** it exits non-zero as `add` would, and writes nothing

#### Scenario: Dry run with an edited copy

- **WHEN** `.apm/skills/tdd/SKILL.md` was edited and the user runs `bind mp/grilling cp/grilling --dry-run`
- **THEN** it exits 1 naming `.apm/skills/tdd`, as `bind` would

#### Scenario: Dry run with an uncached ref

- **WHEN** a git **Source**'s `ref` is not in the cache and the user runs `add mp/tdd --dry-run`
- **THEN** it fetches the commit into a temporary folder, and the cache folder is unchanged

### Requirement: Edit reports the hull diff

An edit with `--dry-run` SHALL print, before its tree, the **Hull diff** of the **Vendored copies** against the
**Hull** it would vendor, in `update`'s form: `hull (+ added, - removed, ~ changed):`, then `+`, `-` or `~` and the
**Skill ID** per **Skill**, sorted, each changed file under a `+` or `~` line as `update` names them; or
`hull unchanged`. A **Skill** is matched to its copy through the lock's **Skill IDs** and **Deployed names**; with no
lock, every **Skill** is `+`. Without `--diff`, when it marks a **Skill** `+` or `~`, it SHALL print
`review: skill-graft <command> <arguments> --dry-run --diff <file>` before its `dry run:` line.

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

- **WHEN** the user runs `add mp/tdd --dry-run` without `--diff`, and `mp/tdd` joins the **Hull**
- **THEN** it prints `review: skill-graft add mp/tdd --dry-run --diff <file>` before its `dry run:` line

#### Scenario: Nothing changed

- **WHEN** `mp/tdd` is already in the **Hull**, through another **Entry**, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints `hull unchanged` and no `review:` line

### Requirement: Edit deployed diff file

An edit with `--diff <file>` SHALL write the **Deployed diff** of its **Hull diff**'s `+` and `~` **Skills** to
`<file>`, refusing, removing and ordering its writes as `update --diff` does: last in a dry run, before
`skill-graft.toml` otherwise, and removed if a later write fails. Its content SHALL follow `update`'s, its source lines
naming each git **Source**'s `ref` once; its header's second line SHALL say it compares the **Vendored copies** against
what the edited config would vendor.

#### Scenario: Diff file

- **WHEN** the user runs `add mp/tdd --dry-run --diff review.diff`, and `mp/tdd` and `mp/grilling` join the **Hull**
- **THEN** `review.diff` starts with the header and the marked **Hull**, then both **Skills**' files as added

#### Scenario: Removed skill

- **WHEN** the user runs `remove mp/tdd --dry-run --diff review.diff`, and `mp/tdd` leaves the **Hull**
- **THEN** `review.diff` holds the line `# - mp/tdd`, and none of `mp/tdd`'s text

#### Scenario: A file it did not write

- **WHEN** the user runs `add mp/tdd --dry-run --diff apm.yml` in a project-scope **Package**
- **THEN** it exits non-zero naming `apm.yml`, which keeps its bytes, before resolving

#### Scenario: Diff with a real edit

- **WHEN** the user runs `add mp/tdd --diff review.diff` and writing `skill-graft.lock` fails
- **THEN** it exits non-zero, `skill-graft.toml`, the lock and `.apm/skills/` keep their bytes, and `review.diff` does
  not exist

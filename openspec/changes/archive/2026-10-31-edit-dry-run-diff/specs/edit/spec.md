# Spec Delta

## ADDED Requirements

### Requirement: Edit dry run writes nothing

`add`, `remove`, `rename`, `bind` and `unbind` with `--dry-run` SHALL check, resolve and print as without it, exiting
with the same code, but SHALL write neither `skill-graft.toml`, `skill-graft.lock`, `.apm/skills/`, `.gitattributes` nor
the cache, nor anything outside a temporary folder it removes before exiting, except the **Deployed diff** file `--diff`
names. It SHALL say `dry run: skill-graft.toml, skill-graft.lock and .apm/skills/ not written`, as its last line on
standard output. An edit that changes no value SHALL print only its notices, as without `--dry-run`, and no `dry run:`
line. A **Patch** failing in a dry run SHALL say, as `update --dry-run` does, that the upstream folder it names was
fetched into a temporary folder, and to run the same command without `--dry-run` to keep it.

#### Scenario: Dry run of an add

- **WHEN** the user runs `add mp/tdd --dry-run` and the edited config resolves
- **THEN** it prints the **Hull diff** and its `dry run:` line, and `skill-graft.toml`, `skill-graft.lock`,
  `.apm/skills/` and the cache folder are unchanged

#### Scenario: Dry run of a failing edit

- **WHEN** the user runs `add mp/notes --dry-run` and `mp/notes` calls `/x`, which matches several other **Sources** and
  no **Bind**
- **THEN** it exits non-zero as `add` would, and writes nothing

#### Scenario: Dry run with an edited copy

- **WHEN** `.apm/skills/tdd/SKILL.md` was edited and the user runs `bind mp/grilling cp/grilling --dry-run`
- **THEN** it exits 1 naming `.apm/skills/tdd`, as `bind` would

#### Scenario: Dry run with an uncached ref

- **WHEN** a git **Source**'s `ref` is not in the cache and the user runs `add mp/tdd --dry-run`
- **THEN** it fetches the commit into a temporary folder, and the cache folder is unchanged

#### Scenario: Dry run checking its target first

- **WHEN** `cp`'s `ref` is not in the cache and the user runs `bind mp/grilling cp/grilling --dry-run`
- **THEN** the cache folder is unchanged, though `bind` reads `cp` before resolving

#### Scenario: Dry run line last on standard output

- **WHEN** `mp/tdd` is already in the **Hull**, through another **Entry**, and the user runs `add mp/tdd --dry-run`
- **THEN** standard error holds the notice that `mp/tdd` was already in the **Hull**, and standard output ends with the
  `dry run:` line

#### Scenario: No-op dry run

- **WHEN** `mp/tdd` is already an **Entry** and the user runs `add mp/tdd --dry-run`
- **THEN** it prints only the notice that `mp/tdd` is already an **Entry**, and no `dry run:` line

#### Scenario: Patch failing in a dry run

- **WHEN** `mp`'s `ref` is not in the cache, a **Patch** of `mp/tdd` fails there, and the user runs
  `add mp/tdd --dry-run`
- **THEN** the error names `mp/tdd` and says to run `skill-graft add mp/tdd` without `--dry-run` to keep what it
  fetched, not to run `update`

### Requirement: Edit reports the hull diff

An edit with `--dry-run` or `--diff` SHALL print, before its tree, the **Hull diff** of the **Vendored copies** against
the **Hull** it would vendor, in `update`'s form: `hull (+ added, - removed, ~ changed):`, then `+`, `-` or `~` and the
**Skill ID** per **Skill**, sorted, each changed file under a `+` or `~` line as `update` names them; or
`hull unchanged`. A plain edit SHALL print as before. A **Skill** is matched to its copy through the lock's **Skill
IDs** and **Deployed names**, and a copy read only as an entry of `.apm/skills/`; one the lock records without a copy,
and every **Skill** with no lock, is `+`, and a **Skill** is `-` only when it leaves the **Hull** and had a copy. A
removed **Skill**'s ID, read from the lock, SHALL be quoted as file paths are. Without `--diff`, when it marks a
**Skill** `+` or `~`, it SHALL print `review: skill-graft <command> <arguments> --dry-run --diff <file>`, each argument
quoted for a POSIX shell, right before its `dry run:` line.

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

#### Scenario: Plain edit unchanged

- **WHEN** the user runs `add mp/tdd` without `--dry-run` or `--diff`
- **THEN** it prints what it printed before, and no **Hull diff**

#### Scenario: A lock pointing outside the copies

- **WHEN** the lock records `mp/tdd` with `deployed = "../../outside"` and no copy deployed under that name, and the
  user runs `add mp/notes --dry-run --diff review.diff`
- **THEN** it reads nothing outside `.apm/skills/`, and prints `mp/tdd` as `+`

#### Scenario: A removed ID holding a control character

- **WHEN** the lock records a **Skill** whose ID holds a line feed and an escape character, and it leaves the **Hull**
- **THEN** its `-` line, and its `# -` line in the diff file, show the ID quoted, on one line

### Requirement: Edit deployed diff file

An edit with `--diff <file>` SHALL write the **Deployed diff** of its **Hull diff**'s `+` and `~` **Skills** to
`<file>`, refusing and ordering its writes as `update --diff` does: last in a dry run, before `skill-graft.toml`
otherwise, and removed if a later write fails. It SHALL remove an earlier file it wrote there once the edit is past its
no-op check, before resolving, and when it fails before its writes went through: an edit that changes no value leaves it
as it was, one that fails leaves none, and one that fails once written, such as on a closed standard output, keeps the
file of what it wrote. Its content SHALL follow `update`'s, its source lines naming each git **Source**'s `ref` as the
lock records it, quoted as file paths are, and as the command would vendor it, `old -> new` when they differ, only the
new one when the lock records none; each line of its marked tree SHALL be escaped as a line of the diff is; its header's
second line SHALL say it compares the **Vendored copies** against what the edited config would vendor.

#### Scenario: Diff file

- **WHEN** the user runs `add mp/tdd --dry-run --diff review.diff`, and `mp/tdd` and `mp/grilling` join the **Hull**
- **THEN** `review.diff` starts with the header and the marked **Hull**, then both **Skills**' files as added

#### Scenario: Removed skill

- **WHEN** the user runs `remove mp/tdd --dry-run --diff review.diff`, and `mp/tdd` leaves the **Hull**
- **THEN** `review.diff` holds the line `# - mp/tdd`, and none of `mp/tdd`'s text

#### Scenario: A file it did not write

- **WHEN** the user runs `add mp/tdd --dry-run --diff apm.yml` in a project-scope **Package**
- **THEN** it exits non-zero naming `apm.yml`, which keeps its bytes, before resolving

#### Scenario: A failed edit leaves no file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `add mp/notes --dry-run --diff review.diff` fails
  because `mp/notes` calls `/x`, which matches several other **Sources** and no **Bind**
- **THEN** `review.diff` no longer exists

#### Scenario: A refused edit leaves no file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `remove mp/typo --diff review.diff` fails because
  `mp/typo` is no **Entry**
- **THEN** `review.diff` no longer exists

#### Scenario: A ref the lock holds

- **WHEN** the lock records `mp`'s `ref` holding a line feed, or no `ref`, and the user runs
  `rename mp/tdd t --dry-run --diff review.diff`
- **THEN** `mp/tdd`'s source line names that `ref` quoted, on one line, or only the new `ref`

#### Scenario: A no-op edit keeps the file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, `mp/tdd` is already an **Entry**, and the user runs
  `add mp/tdd --diff review.diff`
- **THEN** it prints only its notice, and `review.diff` keeps its bytes

#### Scenario: Diff with a real edit

- **WHEN** the user runs `add mp/tdd --diff review.diff` and writing `skill-graft.lock` fails
- **THEN** it exits non-zero, `skill-graft.toml`, the lock and `.apm/skills/` keep their bytes, and `review.diff` does
  not exist

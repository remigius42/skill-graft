# Spec Delta

## MODIFIED Requirements

### Requirement: Deployed diff file

`update --diff <file>` SHALL write the **Deployed diff** of the **Hull diff**'s `+` and `~` **Skills** to `<file>`, its
folders resolved, its last part never followed as a symbolic link. Before any other step it SHALL refuse, naming it, a
`<file>` whose name does not end in `.diff`; that, as given without `..` or once its folders are resolved, lies inside a
folder named `.apm` in any case or a folder holding a `SKILL.md`; that lies in no existing folder; that exists and is
not a regular file; or that is a regular file not starting with the **Deployed diff**'s header, reading no more of it
than the header's first line. So it never replaces a file it did not write, never writes a file a harness loads as a
command, rule or **Skill**, and never blocks on what it reads. Then it SHALL remove a file it wrote before, so a run
that fails leaves none. In a dry run it SHALL write the file last, before any closing line. In a real `update` it SHALL
write the file before `skill-graft.toml` and the lock, and remove it if either of those writes fails.

The file SHALL start with a header saying it holds the **Skills**' text as deployed, **Patches** and **Renames**
applied, at the current `ref`s against the new ones, not what the **Sources** changed upstream, and that it is untrusted
text to read in an editor; its first line SHALL be the same in every **Deployed diff** skill-graft writes. After the
header it SHALL list the new **Hull** as `tree` prints it, each line commented, escaped as a line of the diff is, and
marked `+` or `~` for a **Skill** the **Hull diff** marks so, then one line `# - <skill id>` for each **Skill** it marks
`-`, and no other line for it. When there is no previous **Hull** to compare, it SHALL hold the header, the reason, the
**Hull** with every **Skill** marked `+`, and every **Skill** of the new **Hull** as a `+` **Skill**, all its files
added.

#### Scenario: Diff file

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --diff review.diff`
- **THEN** `review.diff` starts with the header, then `mp/tdd`'s **Deployed diff**

#### Scenario: Existing file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff** and the user runs
  `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds this run's **Deployed diff** only

#### Scenario: Failed run

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `update --dry-run --diff review.diff` fails
  because an **Entry** is gone at the new tip
- **THEN** `review.diff` no longer exists

#### Scenario: A file it did not write

- **WHEN** the user runs `update --dry-run --diff apm.yml` in a project-scope **Package**
- **THEN** it exits non-zero naming `apm.yml`, which keeps its bytes

#### Scenario: A symbolic link

- **WHEN** `review.diff` is a symbolic link and the user runs `update --diff review.diff`
- **THEN** it exits non-zero naming `review.diff`, and the link and its target keep their bytes

#### Scenario: Not a regular file

- **WHEN** the user runs `update --dry-run --diff /dev/zero`, or names a FIFO or a folder
- **THEN** it exits non-zero naming the path, before reading from it or fetching

#### Scenario: Inside the package

- **WHEN** the user runs `update --diff .apm/review.diff`, or `.APM/review.diff` on a filesystem that ignores case, in a
  project-scope **Package**
- **THEN** it exits non-zero naming the path, fetches nothing and writes nothing

#### Scenario: Into the package through a link

- **WHEN** `link` is a symbolic link to the **Package**'s `.apm` folder and the user runs
  `update --diff link/review.diff`, or runs `update --diff sub/../.apm/review.diff`
- **THEN** it exits non-zero naming the path, and writes nothing

#### Scenario: Not a diff file name

- **WHEN** the user runs `update --dry-run --diff .claude/commands/review.md`
- **THEN** it exits non-zero naming the path and asking for a name ending in `.diff`, and writes nothing

#### Scenario: Inside a skill's folder

- **WHEN** the user runs `update --dry-run --diff .claude/skills/mp-tdd/review.diff`, and that folder holds a `SKILL.md`
- **THEN** it exits non-zero naming the path, and writes nothing

#### Scenario: A failed write after the diff

- **WHEN** `update --diff review.diff` resolves, and writing `skill-graft.toml` fails
- **THEN** `review.diff` does not exist

#### Scenario: A failed diff write

- **WHEN** `update --diff review.diff` resolves, and writing `review.diff` fails
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: A failed diff write in a dry run

- **WHEN** `update --dry-run --diff review.diff` resolves, and writing `review.diff` fails
- **THEN** it exits non-zero and prints no `apply:` line

#### Scenario: No previous hull

- **WHEN** a selected git **Source** had no `ref` and the user runs `update --diff review.diff`
- **THEN** `review.diff` holds the header, that reason, and every **Skill** of the new **Hull** as all added

#### Scenario: Patches redone for the new tip

- **WHEN** a **Patch** of `mp/tdd` was redone for `mp`'s new tip and fails at its current `ref`, and the user runs
  `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds every **Skill** of the new **Hull** as all added, and it prints an `apply:` line

#### Scenario: Nothing changed

- **WHEN** every **Skill** keeps its hash and the user runs `update --diff review.diff`
- **THEN** `review.diff` holds the header and says no **Skill** changed

#### Scenario: Skill removed

- **WHEN** at the new tip no **Skill** calls `/grilling` any more, and the user runs
  `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds the line `# - mp/grilling`, even when no **Skill** changed or joined

#### Scenario: In no folder

- **WHEN** the user runs `update --dry-run --diff typo/review.diff`, and there is no folder `typo`
- **THEN** it exits non-zero naming the path, before fetching

#### Scenario: Through a link named .apm

- **WHEN** `proj/.Apm` is a symbolic link to another folder and the user runs `update --diff proj/.Apm/review.diff`
- **THEN** it exits non-zero naming the path, and writes nothing

#### Scenario: Marked hull

- **WHEN** at the new tip `mp/tdd` calls `/grilling` for the first time, and the user runs
  `update --dry-run --diff review.diff`
- **THEN** after its header `review.diff` lists the **Hull** as `tree` prints it, `mp/tdd` marked `~` and `mp/grilling`
  under it marked `+`

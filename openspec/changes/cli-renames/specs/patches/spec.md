## MODIFIED Requirements

### Requirement: Patches apply before references are read

When the walk reaches a **Skill** that `[patches]` names, its **Patches** SHALL apply in list order, each to the result
of the one before, to a copy of its folder; the **Skill**'s **References** SHALL be read from that copy, and `deploy`
SHALL vendor it, **Renames** applied on top. The **Upstream** folder SHALL never change.

#### Scenario: Patch changes the text

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/tdd.patch"]`, which replaces a line of `mp/tdd`'s `SKILL.md`
- **THEN** `deploy` vendors `tdd/SKILL.md` with the replaced line, and the **Source**'s `SKILL.md` keeps its bytes

#### Scenario: Patch adds a reference

- **WHEN** a patch to **Entry** `mp/tdd` adds `/grilling`, which **Upstream** `mp/tdd` does not hold
- **THEN** `mp/grilling` is in the **Hull**

#### Scenario: Patch removes a reference

- **WHEN** **Upstream** `mp/tdd` calls `/grilling`, and a patch to it removes that line
- **THEN** `mp/grilling` is not in the **Hull**

#### Scenario: Patches in order

- **WHEN** `"mp/tdd" = ["patches/a.patch", "patches/b.patch"]`, and `b.patch` changes a line `a.patch` added
- **THEN** both apply, and the vendored `SKILL.md` holds `b.patch`'s line

#### Scenario: Rename on top

- **WHEN** a patch to `mp/tdd` adds `/grilling`, and `[rename]` has `"mp/grilling" = "mp-grilling"`
- **THEN** the vendored `tdd/SKILL.md` holds `/mp-grilling`

#### Scenario: Patch to a sibling file

- **WHEN** a patch to `mp/tdd` changes `refs/loop.md`, adds `refs/new.md` and deletes `refs/old.md`
- **THEN** the vendored `tdd/` folder holds the changed `refs/loop.md` and `refs/new.md`, and no `refs/old.md`

### Requirement: A failing patch is an error

A hunk SHALL apply only where its context matches exactly, moved by whole lines at most; one starting at the file's
first line SHALL match there. Every hunk that does not apply SHALL be reported with its patch file, target file and `@@`
header; a patch git refuses whole SHALL be reported with its patch file and git's message; the **Skill**'s later
**Patches** SHALL be reported as not tried. Any failure SHALL make the command exit non-zero and write nothing.

#### Scenario: Context moved

- **WHEN** **Upstream** `SKILL.md` gained three lines above a hunk in the middle of the file since the patch was written
- **THEN** the hunk applies

#### Scenario: Anchored at the start

- **WHEN** a hunk's context starts at line 1 of `SKILL.md`, and **Upstream** `SKILL.md` gained a line above it
- **THEN** the hunk fails

#### Scenario: Upstream ships a reject file

- **WHEN** the **Upstream** folder holds `notes.md.rej`, and a patch fails because `refs/old.md` is gone
- **THEN** the error passes on git's message and names no hunk of `notes.md`

#### Scenario: Context changed

- **WHEN** a hunk's context line is no longer in the **Upstream** `SKILL.md`
- **THEN** `resolve` exits non-zero naming the patch file, `SKILL.md` and the hunk's `@@` header, and writes no lock

#### Scenario: Every failing hunk named

- **WHEN** two of a patch's three hunks no longer apply
- **THEN** the error names both hunks' `@@` headers

#### Scenario: Patch refused whole

- **WHEN** a patch changes `refs/old.md`, which the **Upstream** folder no longer has
- **THEN** the command exits non-zero naming the patch file and passing on git's message

#### Scenario: Later patch not tried

- **WHEN** `"mp/tdd" = ["patches/a.patch", "patches/b.patch"]`, and `a.patch` fails
- **THEN** the error names `a.patch`'s failure and says `b.patch` was not tried

#### Scenario: Build writes nothing

- **WHEN** a patch fails during `deploy`
- **THEN** `.apm/skills/`, the lock and `apm` are untouched

### Requirement: Patches need git

Applying a **Patch** SHALL run `git`; without `git` on `PATH`, it SHALL be an error saying `[patches]` needs it. A
configuration without **Patches** reached by the walk SHALL not need `git` for them.

#### Scenario: No git

- **WHEN** `git` is not on `PATH` and a **Hull** **Skill** has a patch
- **THEN** the command exits non-zero saying `[patches]` needs `git`

#### Scenario: Path sources without patches

- **WHEN** `git` is not on `PATH`, every **Source** is a path **Source**, and `[patches]` is empty
- **THEN** `deploy --no-apm-install` succeeds

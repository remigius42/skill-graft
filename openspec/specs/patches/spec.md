# patches Specification

## Purpose

Applies the user's **Patches** to a **Skill**'s **Upstream** text before its **References** are read, so a **Patch** can
change what a **Skill** says and what it reaches, and fails loudly when it no longer fits.

## Requirements

### Requirement: Patches apply before references are read

When the walk reaches a **Skill** that `[patches]` names, its **Patches** SHALL apply in list order, each to the result
of the one before, to a copy of its folder; the **Skill**'s **References** SHALL be read from that copy, and `build`
SHALL vendor it, **Renames** applied on top. The **Upstream** folder SHALL never change.

#### Scenario: Patch changes the text

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/tdd.patch"]`, which replaces a line of `mp/tdd`'s `SKILL.md`
- **THEN** `build` vendors `tdd/SKILL.md` with the replaced line, and the **Source**'s `SKILL.md` keeps its bytes

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

### Requirement: Patch paths

A patch's paths SHALL be relative to the **Skill**'s folder with one leading component stripped (`a/SKILL.md`), as
`git diff --relative` inside the folder or `diff -ruN base/ edited/` run from their parent writes them. Neither the
user's git configuration nor a repository enclosing the copy or the **Upstream** folder SHALL change what applies or
what it writes.

#### Scenario: Diff of two folders

- **WHEN** the patch is the output of `diff -ruN upstream/ edited/` for two copies of the **Skill**'s folder
- **THEN** it applies

#### Scenario: User git config

- **WHEN** the user's git config sets `apply.whitespace = fix` and `apply.ignoreWhitespace = change`, and a patch adds a
  line ending in spaces
- **THEN** the vendored line keeps its spaces, and a hunk whose context differs from the **Upstream** text only in
  spacing fails

#### Scenario: Config in the environment

- **WHEN** the environment sets `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=apply.whitespace` and `GIT_CONFIG_VALUE_0=fix`,
  and a patch adds a line ending in spaces
- **THEN** the vendored line keeps its spaces

#### Scenario: Source is a repository

- **WHEN** path **Source** `own` is a git repository whose root is the **Skill** `own/chisel`, and a patch names
  `a/SKILL.md`
- **THEN** it applies to `own/chisel`'s `SKILL.md`

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

- **WHEN** a patch fails during `build`
- **THEN** `.apm/skills/`, the lock and `apm` are untouched

### Requirement: One run reports every failure

A **Skill** whose patch failed SHALL not have its **References** read, and the walk SHALL go on with the other
**Skills** it reaches, so one run reports the failures of every **Skill** reached. Another error that stops the walk
SHALL be reported after the patch failures collected so far. The warnings for `[rename]`, `[patches]` and `[bind]` keys
no **Hull** **Skill** uses SHALL be left out, as the **Hull** is incomplete.

#### Scenario: Two skills fail

- **WHEN** **Entries** `mp/tdd` and `mp/notes` each have a failing patch
- **THEN** one `resolve` reports both

#### Scenario: Another error after a patch failure

- **WHEN** **Entry** `mp/tdd`'s patch fails, and **Entry** `mp/notes` calls `/x`, bound to the missing `own/x`
- **THEN** `resolve` reports `mp/tdd`'s failure, then the missing `own/x`

#### Scenario: Reached only through a failed skill

- **WHEN** `mp/tdd`'s patch fails, `mp/tdd` calls `/grilling`, `[rename]` has `"mp/grilling" = "g"`, and nothing else
  calls `/grilling`
- **THEN** `resolve` reports the failure and no warning that `mp/grilling` is not in the **Hull**

### Requirement: Patch limits

A **Patch** SHALL change, add or delete files inside the **Skill**'s folder only. A patched copy without `SKILL.md`, or
whose name (`name:`, else the folder name) differs from the **Upstream** one, SHALL be a failure of that patch naming it
and pointing at `[rename]`. The patched copy SHALL pass the checks the **Upstream** folder passes (symlinks, special
files), and the **Upstream** folder SHALL pass them before it is copied. Every message SHALL name a file by its
**Upstream** path or its path inside the **Skill**, never by the temporary copy's.

#### Scenario: Name changed

- **WHEN** a patch changes `mp/tdd`'s `name: tdd` to `name: tdd2`
- **THEN** the command exits non-zero naming the patch and `[rename]`

#### Scenario: Name added

- **WHEN** **Upstream** `SKILL.md` of `mp/tdd`, in folder `tdd`, has no `name:`, and a patch adds `name: other`
- **THEN** the command exits non-zero naming the patch and `[rename]`

#### Scenario: SKILL.md deleted

- **WHEN** a patch deletes `mp/tdd`'s `SKILL.md`
- **THEN** the command exits non-zero naming the patch

#### Scenario: Path outside the skill

- **WHEN** a patch names `a/../outside.md`
- **THEN** the command exits non-zero, and no file outside the copy is written

#### Scenario: Symlink leaving the skill

- **WHEN** a patch creates `link.md` as a symlink to `/etc/hostname`
- **THEN** the command exits non-zero naming the patch and `link.md` as pointing outside the **Skill**, and no temporary
  path

#### Scenario: Symlink within the skill

- **WHEN** a patch creates `link.md` as a symlink to `SKILL.md`
- **THEN** the vendored copy holds `link.md` with `SKILL.md`'s content

#### Scenario: Upstream checked first

- **WHEN** a patched **Skill**'s **Upstream** folder holds a symlink to a file outside it
- **THEN** the command exits non-zero naming the symlink, and nothing outside the **Skill** is copied

#### Scenario: Mode change

- **WHEN** a patch written by `git diff` makes `run.sh` executable
- **THEN** the vendored `run.sh` is executable

#### Scenario: Read-only upstream

- **WHEN** a patched **Skill**'s **Upstream** folder and files are read-only
- **THEN** the patch applies, and the **Upstream** folder keeps its bytes and modes

### Requirement: Patches need git

Applying a **Patch** SHALL run `git`; without `git` on `PATH`, it SHALL be an error saying `[patches]` needs it. A
configuration without **Patches** reached by the walk SHALL not need `git` for them.

#### Scenario: No git

- **WHEN** `git` is not on `PATH` and a **Hull** **Skill** has a patch
- **THEN** the command exits non-zero saying `[patches]` needs `git`

#### Scenario: Path sources without patches

- **WHEN** `git` is not on `PATH`, every **Source** is a path **Source**, and `[patches]` is empty
- **THEN** `build --no-install` succeeds

### Requirement: Unused patches warn

A `[patches]` key naming no **Hull** **Skill** SHALL be a warning naming the key. Files in `patches/` that no key lists
SHALL be ignored.

#### Scenario: Patch outside the hull

- **WHEN** `[patches]` has `"mp/notes" = ["patches/notes.patch"]`, and `mp/notes` is not in the **Hull**
- **THEN** the command warns naming `mp/notes`, and succeeds

#### Scenario: Unlisted file

- **WHEN** `patches/old.patch` exists and no key lists it
- **THEN** the command says nothing about it

### Requirement: A file a patch empties is deleted

A file a plain `diff` **Patch** leaves empty that was not empty before it SHALL be deleted from the patched copy, and
each folder that deletion leaves empty, as `git` deletes, whichever `diff` wrote it: `diff -N` writes a deleted file as
one emptied, and only GNU `diff`'s epoch timestamp tells `git` the two apart. A file empty in the **Upstream** folder
SHALL stay. A git-format **Patch** (`diff --git`), whose headers say what it deletes, SHALL apply as `git` applies it.

#### Scenario: Deleted by a diff without GNU timestamps

- **WHEN** a patch to `mp/tdd` deletes `refs/old.md`, written as `diff -ruN` writes it but with a `+++` timestamp other
  than the epoch, as the BSD `diff` of macOS writes it
- **THEN** the vendored `tdd/` folder holds no `refs/old.md`

#### Scenario: Folder left empty

- **WHEN** `refs/old.md` is the only file in `mp/tdd`'s `refs/`, and a patch deletes it with a `+++` timestamp other
  than the epoch
- **THEN** the vendored `tdd/` folder holds no `refs/`, as with GNU `diff`

#### Scenario: Folder replaced by a file

- **WHEN** a patch to `mp/tdd` deletes `refs/old.md`, the only file in `refs/`, and adds a file `refs`
- **THEN** the vendored `tdd/` folder holds the file `refs`

#### Scenario: SKILL.md emptied

- **WHEN** a patch to `mp/tdd` leaves `SKILL.md` empty, with a `+++` timestamp other than the epoch
- **THEN** the command exits non-zero naming the patch as deleting `SKILL.md`

#### Scenario: Empty upstream file

- **WHEN** `mp/tdd` holds an empty `refs/.keep`, and a patch changes `SKILL.md` only
- **THEN** the vendored `tdd/` folder holds the empty `refs/.keep`

#### Scenario: Git-format patch empties a file

- **WHEN** a `git diff` patch to `mp/tdd` empties `notes.md`, without `deleted file mode`
- **THEN** the vendored `tdd/` folder holds `notes.md`, empty

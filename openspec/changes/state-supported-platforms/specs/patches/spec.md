# Spec Delta

## ADDED Requirements

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

#### Scenario: SKILL.md emptied

- **WHEN** a patch to `mp/tdd` leaves `SKILL.md` empty, with a `+++` timestamp other than the epoch
- **THEN** the command exits non-zero naming the patch as deleting `SKILL.md`

#### Scenario: Empty upstream file

- **WHEN** `mp/tdd` holds an empty `refs/.keep`, and a patch changes `SKILL.md` only
- **THEN** the vendored `tdd/` folder holds the empty `refs/.keep`

#### Scenario: Git-format patch empties a file

- **WHEN** a `git diff` patch to `mp/tdd` empties `notes.md`, without `deleted file mode`
- **THEN** the vendored `tdd/` folder holds `notes.md`, empty

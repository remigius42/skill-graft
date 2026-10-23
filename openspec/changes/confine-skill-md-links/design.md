# Design

## Context

`discovery.index` calls `read_name` on every folder `_skill_folders` finds, in every **Source**, and `hull.walk` runs
`files.check_files` only later, and only on **Hull** **Skills**. `os.walk` lists a `SKILL.md` symlink among
`filenames`, so `confined` (set for git **Sources**) limits the folders entered but never the `SKILL.md` read. The cache
export writes committed symlinks as they are, absolute targets included (`cache._export`). Reproduced through a real
`Cache.checkout`: a `SKILL.md` linked to an outside file put that file's `name:` value into the `invalid` error.

## Goals / Non-Goals

**Goals:**

- In a confined **Source**, no file outside a **Skill**'s folder is opened to read its `SKILL.md`.
- In any **Source**, no `SKILL.md` that is not a regular file is opened.

**Non-Goals:**

- Confining path **Sources**' links: they may lead anywhere, to a regular file.
- Refusing symlinks at export: the spec keeps them, and links inside a **Skill** are vendored as copies.
- Other files: `check_files` already guards them before `hidden.scan` and `references.scan` read anything.

## Decisions

- **Checks in `index` and `read_name`, in this order; no rule shared with `check_files`.**

  1. Confined: `os.path.realpath(SKILL.md)` must be inside the **Skill**'s resolved folder (`folder.resolve()`: the
     walk may reach the folder through a symlinked one). First, so nothing outside a git **Source** is ever stat'ed or
     opened, and every outside link gets the same message whatever it leads to.
  1. Always: `os.stat` the `SKILL.md`, links followed, and require `S_ISREG`; any `OSError` (missing, loop, `EACCES`)
     refuses it too, its message adding the cause. Not `Path.is_file`, which re-raises `EACCES` on Python 3.11 to 3.13
     past `index`'s handler, nor `os.path.isfile`, which drops the cause.
     Before opening, so no device is opened at all: opening some has side effects.
  1. `read_name` opens with `O_RDONLY | O_NONBLOCK`, `fstat`s the descriptor, requires `S_ISREG` again, and reads from
     it. That closes the race of a regular file swapped for a FIFO after step 2; `O_NONBLOCK` does nothing to a regular
     file.

  The other clauses of `check_files` cannot fire here: git commits no device or FIFO, and `os.walk` lists a link to a
  folder among folders, never as `SKILL.md`. Alternative: extract `check_files`' per-link rule and share it. Its
  messages name the target, and its folder clauses never fire here.

- **A refused `SKILL.md` makes the name unreadable, filed under its folder name.** That is what `Index.unreadable` is
  for, and the `hull` spec already says how such a **Skill** acts: an **Entry** or **Reference** naming that folder
  gets the error, others never see it. Alternative: fail the whole command. Then any **Skill** in a **Source**, used or
  not, would break every build.

- **Messages name the `SKILL.md` by its full path, as `read_name`'s do, never its target**:
  `<full path>/SKILL.md: a symlink leading outside its skill`, and `<full path>/SKILL.md: not a regular file`, followed
  by `: <cause>` (the `OSError`'s `strerror`, such as `Permission denied`) when the `stat` fails. The confined check
  runs first and has one message whatever the target is, so it tells nothing about it; a cause is told only for a
  `SKILL.md` that stays inside its **Skill** in a git **Source**, or one in a path **Source**. `check_files` still
  prints a link's target; that is the path the link's author wrote, resolved, not any file's content, and stays as it
  is.

## Risks / Trade-offs

- **Risk:** a refused `SKILL.md` files its folder name as unreadable, so an **Entry** for another **Skill** that
  carries that name becomes ambiguous and fails, where today it may resolve. → As for any unreadable name, skill-graft
  never picks silently between a known match and one it cannot read; the error names both.
- **Risk:** a `SKILL.md` linked to a sibling **Skill**'s file in the same repository is now refused even outside the
  **Hull**. → `build` already refused it inside the **Hull**; it is the case this change closes.
- **Risk:** the file changes between the checks and the read. → The `fstat` on the open descriptor decides what is read;
  the cache tree is written once and renamed into place.

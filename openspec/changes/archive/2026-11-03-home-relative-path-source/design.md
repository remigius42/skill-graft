# Design

## Context

`config._source_folder` resolves a path **Source**'s `path` (`~` expanded, relative to the config's folder, symlinks
followed) into `PathSource.folder`, and keeps nothing else. `lock.render` wrote that folder: relative to the **Package**
when, in project scope, it is inside the project root, else absolute. Nothing reads the lock's `path` back: `lock.drift`
drops it. `update`'s nothing-to-apply check compares whole parsed locks, `path` included. Every command that writes the
lock (`resolve`, `deploy`, `update`, and the edit commands through `edit._finish`) goes through `transaction.resolving`;
`deploy --into` passes its own `lock_file`, and dry runs pass `write=False`.

## Goals / Non-Goals

**Goals:**

- A committed project lock reads the same on every machine when its path **Sources** sit inside the project or under
  `~/`.
- Whoever writes a lock that records a path absolute in project scope is told so.

**Non-Goals:**

- Changing how `path` is resolved or checked, or what the folder is used for: discovery, hashing and the overlap checks
  still use the resolved folder.
- User scope's lock.

## Decisions

- **Record the `path` as written when it starts with `~/`, not the resolved folder made home-relative.** `PathSource`
  gains the string as written. Deriving `~/<rest>` from the resolved folder fails for `~/skills` symlinked outside the
  home folder (it resolves elsewhere), and for a home that is itself a symlink; the written form is what the user meant
  to share. The written string is the user's own (path **Sources** are trusted, see build-verifies-lock's design), and
  the lock's `path` is provenance only, never read back, so it opens no path a hostile upstream controls.
- **Normalized by segment, never across `..`.** The part after `~/` is split on `/`, empty and `.` segments dropped, so
  `~/skills/`, `~//skills` and `~/./skills` record `~/skills`. A path with any `..` segment is recorded absolute and
  warned of: `~/x/../skills` names another folder when `~/x` is a symlink, as the folder is resolved with symlinks
  followed, and `~/../shared` leaves the home folder, which differs between Linux and macOS. A segment merely starting
  with `..` (`~/..skills`) is a name, and portable. Alternatives rejected: verbatim, which churns the lock on an edit
  that changes no meaning; lexical normalization of the whole path, which collapses `x/..` lexically and keeps a leading
  `//`.
- **`~user` is not portable.** `~alice/skills` names one user's home, which another machine may lack or give another
  meaning; it is recorded absolute and warned of. `Path.expanduser` raises `RuntimeError` for a user that does not
  exist; one helper in `pipeline/config.py` expands `~` for both `path` and `[patches]` files, turning it into a
  `SkillGraftError` naming the path, so neither prints a traceback.
- **Inside the project wins.** The check for inside the project root still runs first on the resolved folder, so
  `~/repo/skills` in a project at `~/repo` stays `../../skills`, as today.
- **One function decides portability.** `lock.portable_path(scope, source)` returns the recorded form for a path
  **Source** inside the project or under `~/` in project scope, else `None`. `render` writes its result or the absolute
  folder; the warning fires exactly when it is `None` in project scope. Alternative rejected: the warning
  re-implementing the check, where a fix to one copy would leave the two disagreeing.
- **The warning sits in `transaction.resolving`, when the lock is the package's.** Every command that writes the
  package's lock goes through it, so `add`, `rename` or `update` committing an absolute path warns as `resolve` does; a
  dry run warns too, since applying it would write that lock. `deploy --into` passes its own `lock_file` and leaves the
  package's lock alone, so it does not warn; `tree` and `why` never call `resolving`. Alternatives rejected: `resolve`
  and `deploy` only, which commits the path silently through every other writer; `config.parse`, which reaches every
  command. It fires on every such run: the config itself is what is machine-specific, so no state could make it once.
  Wording: see task 2.1.
- **`update`'s nothing-to-apply check drops path Sources' `path`, through `drift`'s rule.** It already means "the lock
  records the same hull"; a recorded folder is not part of the hull, as `drift` holds. Without this, an older lock's
  absolute folder, or any lock written on another machine with an absolute `path`, makes `update --dry-run` ask to apply
  a change that only rewrites provenance. `lock.without_paths(data, path_aliases)`, taken out of `drift`'s `shape`,
  drops them for both, and leaves a lock whose `sources` are not a table of tables (the check `_well_formed` shares) as
  it is, so a malformed one is a difference, as the plain `==` makes it today. `config.path_aliases` gives `update` and
  `deploy` the same aliases. Alternative rejected: a second copy in `update.py` of which fields a path **Source** may
  change.

## Risks / Trade-offs

- \[A teammate's `~/skills` holds different skills\] → as today: their hashes differ, and `deploy` vendors the changed
  text and names it (deploy's "Changed path Source deployed"); only the `path` line stops churning.
- \[A lock committed before this change records `~/`-sourced folders absolute\] → the next command that writes the lock
  rewrites that line once; `deploy` treats the folder as no difference, so it does not refuse, and `update --dry-run`
  ignores it.
- \[`~/skills` is a symlink into the project on one machine only\] → that machine records the folder relative to the
  **Package**, the others `~/skills`, and each rewrites the line: "inside the project wins" is decided on the resolved
  folder. Rare; rejecting symlinked path **Sources** would break the common `~/skills` symlinked into a dotfiles folder.

## Migration Plan

None beyond the one-line lock rewrite above. Rollback: an older skill-graft reads `~/skills` as a string it never uses,
and writes the absolute folder again; until it does, its `update --dry-run` prints an `apply:` line where it would print
`nothing to apply`, since it compares the whole lock.

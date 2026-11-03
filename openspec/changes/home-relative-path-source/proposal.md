# Proposal

## Why

In project scope, a path **Source** outside the project root, such as `path = "~/skills"`, is recorded in the committed
`skill-graft.lock` as its absolute folder (`/home/me/skills`). Each teammate's `resolve` or `deploy` then rewrites that
line to their own folder, so the lock churns between machines and carries the author's home path. The config already
says the same thing on every machine with `~`; the lock should too.

## What Changes

- In project scope, the lock records a path **Source** whose `path` is `~` or starts with `~/` as written, normalized
  (`~/skills/` and `~//skills` both record `~/skills`), unless its folder is inside the project root, which stays
  relative to the **Package**. The folder is still resolved as today; only what the lock records changes.
- Every other path **Source** outside the project root stays recorded absolute: `/opt/skills`, `../shared-skills`, the
  home folder written out, `~alice/skills` (one named user's home), and a `~/` path with a `..` segment (`~/../shared`,
  or `~/x/../skills`, which a symlinked `~/x` sends elsewhere). In project scope, each command that writes the package's
  lock, or would in its dry run, warns of each, naming the alias and the folder: other machines need that folder at the
  same place. `explain`, and `deploy --into`, which leaves the package's lock alone, do not.
- `~alice/…` naming a user that does not exist, in a `path` or a `[patches]` file, is an error naming the path, not a
  traceback.
- `update --dry-run` ignores path **Sources**' `path` lines when deciding there is nothing to apply, as `deploy` already
  does when comparing with the lock.
- User scope is unchanged: its lock is not shared, and records absolute folders as before.
- The README's paragraph on committing a project **Package** names `~/` as the other machine-independent form.

Not in scope: environment variables in `path` (the trust model would allow them, but `~/` covers the shared case without
a new syntax), and any change to how `path` is resolved or checked.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `resolve`: "Lock content" records a `~/` path **Source** as written, without empty or `.` segments, in project scope;
  "Lock records upstream folders and patches"'s "Same lock on another machine" scenario covers such **Sources**; "Lock
  is deterministic" names only folders recorded absolute as machine-dependent.
- `config`: "Path sources": a `~user` path naming no user is an error. New requirement: commands that write the
  package's lock warn of a project-scope path **Source** recorded absolute.
- `deploy`: "Changed path Source deployed" writes the paths path **Sources** are recorded at, not their folders; new
  scenarios: a lock recording `~/skills` is left as committed on another machine, and an older lock's absolute folder is
  rewritten to `~/skills`; "Path source elsewhere on another machine" uses an absolute `path`.
- `update`: "Update to the hull vetted": nothing to apply ignores path **Sources**' `path` lines.

## Impact

- `src/skill_graft/pipeline/config.py`: `PathSource` keeps the `path` as written; one helper expands `~` for sources and
  patches, a `~user` naming no user a `SkillGraftError`.
- `src/skill_graft/pipeline/lock.py`: one function decides a path **Source**'s portable recorded form, or none; the
  lock's `path` and the warning both use it.
- `src/skill_graft/commands/transaction.py`: `resolving` adds the warning when the lock is the package's own.
- `src/skill_graft/commands/update.py`: the nothing-to-apply comparison drops path **Sources**' `path` through `drift`'s
  rule, taken out into `lock.py`.
- Tests in `tests/pipeline/test_lock.py`, `tests/pipeline/test_config.py`, `tests/commands/test_scope.py`,
  `tests/commands/test_deploy.py`, `tests/commands/test_update.py`, `tests/cli/test_warnings.py`.
- `README.md`, `docs/design.md` if it describes the lock's `path`, `CHANGELOG.md` at archive.
- A committed lock written before this change rewrites its absolute `~/`-sourced folder once, on the next command that
  writes the lock. `deploy` already treats a path **Source**'s folder as no difference, so it does not refuse.

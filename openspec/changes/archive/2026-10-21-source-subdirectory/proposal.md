# Proposal

## Why

A git **Source** is always walked from the repository root, so a repository holding several plugins cannot be
used. <https://github.com/cursor/plugins> has 169 **Skills** in 19 plugin folders, and 65 names occur more than
once (`pstack/skills/tdd`, `harness/pstack/claude-code/skills/tdd`). **Skill IDs** must be unique within a
**Source**, so an **Entry** `cp/tdd` fails with "several skills match". A path **Source** can already point at a
subfolder; a git **Source** cannot. The in-flight `graft-check` change needs it too: it installs one skill from
this repository's `skills/`, and walked from the root, the repository's six `.claude/skills/openspec-*` skills
would become candidates for cross-source resolution in the user's **Hull**.

## What Changes

- **`subdirectory`**: a new optional key on git **Sources**, `subdirectory = "pstack/skills"`. Every command that
  reads the **Source** walks only that folder of the export at `ref` (or at the tip during `update`), as if it
  were the repository root. Discovery follows only symlinked folders that stay inside it. The name follows
  uv's `{ git, subdirectory }` and pip's `#subdirectory=`.
- **Validation at load**: a non-empty relative path of `/`-separated segments, none empty, `.`, `..` or `.git`, with no
  control characters and no `.apm/skill-graft` in it. Anything else is an error naming
  `sources.<alias>.subdirectory`. On a path **Source** the key is unsupported, as `ref` is there: point `path` at
  the folder instead.
- **Checked at the commit read**: a subdirectory missing at that commit (names compared exactly, case included),
  one that is not a folder there, or one with a symlink anywhere in its path is an error naming the alias, the
  subdirectory and the commit. This happens in `resolve`, `build`, `update` and every other command that reads the
  **Source**, including `add` and `bind` for a **Skill** of another **Source**, since every **Source** is read, as
  with a missing `ref`. `update` therefore refuses to move `ref` to a tip where the subdirectory is gone, and
  leaves the TOML and the lock unchanged.
- **Lock**: a git **Source**'s table records `subdirectory` when it is set. A **Skill**'s `upstream` stays a path
  relative to the repository root, the subdirectory included (`pstack/skills/tdd`), so the export at `ref` joined
  with `upstream` is the **Skill**'s folder without knowing the subdirectory. The lock `version` stays 1.
- `why` already prints the absolute upstream folder, so its output needs no change. The `init` template, the README
  config section and `docs/design.md` show the key, and CONTEXT.md's **Source** entry mentions it.

Out of scope: `subdirectory` on path **Sources**; several subdirectories per **Source** (declare one alias per
folder, all sharing the URL's cache); a command that sets the key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `config`: `subdirectory` becomes a supported, validated key, and only beside `git`.
- `git-sources`: a git **Source**'s folder is its subdirectory of the export, checked at the commit read.
- `resolve`: the lock records a source's `subdirectory`, and `upstream` stays relative to the repository root.
- `update`: a tip without the subdirectory fails resolution, so no `ref` moves.

## Impact

- Code: `config.py` (key, validation, `GitSource.subdirectory`), `resolve.py` (`folders` returns the checked
  subdirectory; the hull's roots are the repository's), `hull.py`, `lock.py` (source `subdirectory`), `init.py`
  (template), with tests.
  `cache.py` is unchanged: exports stay one per URL and commit, shared by aliases that differ only in
  subdirectory.
- Docs: `README.md`, `docs/design.md`, `CONTEXT.md`.
- Unblocks `graft-check` (branch `feat/opsx-graft-check`), which lands after this.

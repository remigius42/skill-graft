# Proposal

## Why

A user who wants a **Skill** to say something else (drop a step, add a `/call`) has no way to do it short of
forking its **Source**. A **Patch** keeps the change as a unified diff against the **Upstream** text, applied on
every build, and fails loudly when an `update` moves the **Upstream** text under it (ADR 0001).

## What Changes

- **Patches**: a new `[patches]` table, `"<skill id>" = ["patches/x.patch", …]`, paths relative to the folder
  holding `skill-graft.toml`. When the walk reaches a **Skill**, its **Patches** apply in list order to a copy of
  its folder, before its **References** are scanned, so a **Patch** can add or remove **References** and change
  the **Hull**; **Renames** then apply on top. `build` vendors the patched copy.
- **Strict application**: `git apply -p1`, no fuzz, the user's git config ignored. Every failing hunk is named
  (patch file, target file, `@@` header), and a patch git refuses whole is named with git's message. One run
  reports every failure among the **Skills** it reaches; `resolve`, `build` and `update` then fail and write
  nothing.
- **Limits**: a **Patch** may change, add or delete any file in the **Skill**'s folder, but must not delete
  `SKILL.md` or change the **Skill**'s name (a new name is a **Rename**). The patched copy passes the same file
  checks as the **Upstream** one. A `Binary files … differ` line, which `diff -ru` writes for a change it cannot
  express, is an error.
- **Config errors and warnings**: a listed patch file that is missing or unreadable, or listed twice under one
  key, is an error, used or not; a key naming no **Hull** **Skill** is a warning.
- **Update**: a failing patch at the new tips leaves `ref` and the lock as they are and names each failing
  **Skill**'s **Upstream** folder at the tip to redo the patch against. The hull diff, when today's patches fail
  at the current refs, says so in one line.
- **Lock and tree**: each **Hull** **Skill** records its absolute `upstream` folder, and a patched one its
  `patches` in apply order; hashes cover the patched copy. The tree marks a patched **Skill** `(patched)`.

Out of scope: a command that writes patches (`docs/design.md` gives the manual recipe), binary hunks, marking
edges a patch added or removed, `why` and `tree`.

## Capabilities

### New Capabilities

- `patches`: applying a **Skill**'s **Patches** before its **References** are scanned, their limits, and how
  failures are reported.

### Modified Capabilities

- `config`: `[patches]` becomes supported, with its path, type and duplicate rules.
- `resolve`: the lock records `upstream` and `patches`; the tree marks patched **Skills**.
- `update`: a failing patch names the **Upstream** folder at the tip; the hull diff's message when patches fail at
  the current refs.

## Impact

- New: `src/skill_graft/patch.py` (copy, `git apply`, checks, failure report), with tests.
- Changed: `config.py` (`[patches]`, files read at load), `hull.py` (patch before scan, collect failures, `Hull`
  gains each **Skill**'s **Upstream** folder), `resolve.py` and its callers in `cli.py` and `update.py` (a
  temporary folder for each resolution, alive until vendoring and hashing finish), `lock.py` (`upstream`,
  `patches`, `(patched)`), `update.py` (failure hint, hull diff message).
- `docs/design.md`, `README.md`: patches built.
- Behavior: every lock gains `upstream` on each **Skill**, so existing locks change once. A path-only setup needs
  `git` only once it declares a patch.

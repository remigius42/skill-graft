# Design

## Context

From renames: `hull.walk(config, indexes)` finds each **Skill**'s folder with `discovery.find`, runs
`check_files` on it, then `references.scan`; `Hull.skills` maps each **Skill** to that folder, and everything
downstream reads it: `rename.rewrites` (spans checked against the bytes scanned), `lock.skill_hashes`,
`vendor.vendor`. Git folders are cache exports, immutable and shared. `git.run` strips the variables that point
git at another repository but keeps the user's git config; `vendor.vendor` copies with `copytree`. `cli`
resolves, then vendors and hashes; `update` resolves twice (`_previous` at the current refs, then the tips), the
dry run inside a temporary cache. Tests: `tests/conftest.py` (`HOME` in `tmp_path`, `GIT_CONFIG_GLOBAL` pointed
at an empty file, `skill`, `write_config`, `Upstream`). `docs/design.md` § Patches holds the decisions this
design implements.

## Goals / Non-Goals

**Goals:** a patched **Skill** is, to everything after the walk, just a folder: the copy. The vendored bytes stay
a pure function of the **Source** folders, the TOML and the patch files, whatever the machine's git config.

**Non-Goals:** a patch-writing command; binary hunks; caching patched copies; telling which edges a patch added.

## Decisions

- **Patch in the walk, then forget it**: for each **Skill** reached, `walk` finds the **Upstream** folder, runs
  `check_files` on it, and if `config.patches` names the **Skill**, calls `patch.apply`, which returns the patched
  copy, checked with `check_files`; `scan` reads it. `Hull.skills` holds the copy, so rewrites,
  hashes and vendoring need no change. `Hull` gains `upstream: dict[SkillId, Path]` (every **Skill**) and
  `patches: dict[SkillId, list[str]]` (patched **Skills**, paths as written), for the lock and the tree.
  Alternative, patching at vendor time: the scan would read unpatched text, and a patch could not change the
  **Hull** (ADR 0001).

- **A temporary folder per resolution, owned by the caller**: `resolve.resolve(config, folders, work)` and
  `walk(..., work)` take the folder copies go into, `work/<alias>/<name>/<upstream folder name>` (the last part
  keeps `read_name`'s folder fallback). `cli` opens one `tempfile.TemporaryDirectory(prefix="skill-graft-")`
  around resolving, vendoring and hashing; `update` opens one for the tips and another inside `_previous`, so two
  resolutions of one **Skill** never share a copy. Alternative, `walk` owning it: the copies would be gone before
  `vendor` reads them.

- **One copy helper**: `files.copy_skill(source, target, copy_function=shutil.copy2)`, `shutil.copytree` without
  `.git`, following symlinks; `vendor.vendor` passes its rewriting `copy_function`, `patch.apply` the default. So
  the patched copy holds exactly what vendoring would copy, and a later change to what is skipped reaches both.

- **`patch.apply(skill, upstream, files, work) -> Path`**: `files.copy_skill(upstream, copy)` (`check_files` has
  made sure links lead to files inside), then owner write permission added to every file and folder of the copy,
  so a read-only **Upstream** folder (a Nix store, `0555` folders) never blocks `git apply`; the exec bit is kept.
  Then per file, `git.apply(copy, data)`. After the last, `SKILL.md` must be a file, `check_files(copy)` must
  pass, and `discovery.read_name(copy)` must equal `read_name(upstream)`; any `SkillGraftError` from these (a
  link out, an unsupported `name:` form, non-UTF-8) is re-raised as `PatchFailed` naming the patch, a changed name
  pointing at `[rename]`. Paths in these messages are relative to the **Skill**, never the copy's.
  `PatchFailed` is a `SkillGraftError`, so one that escapes is still a clean error.

- **`git.call(*args, cwd, env, input) -> CompletedProcess`**: the part of `git.run` that builds the environment
  (without `REDIRECTS`) and maps a missing `git` to an error, now shared; `git.run` checks the exit code on top.
  `git.apply(folder, patch) -> (ok, stderr)` calls `git apply -p1 --reject --whitespace=nowarn -`, the patch on
  stdin, `cwd=folder`, with every `GIT_CONFIG*` variable removed and `HOME` and `XDG_CONFIG_HOME` pointed at an
  empty folder under `work`, `GIT_CONFIG_NOSYSTEM=1`, and `GIT_CEILING_DIRECTORIES=<folder's parent>`: no user,
  system or environment config (`apply.*`, `core.autocrlf`, `core.whitespace`, …), on any git version, and no
  enclosing repository changes the result; the copy has no `.git` of its own. A missing `git` raises "`[patches]`
  needs git: no `git` on PATH". It returns instead of raising because a failure is reported, not fatal on the
  spot. Alternative, a Python applier: about 150 lines for new files, deletions and modes that git already gets
  right, and strict without fuzz.

- **Failures from `.rej` files**: before each `git.apply`, `patch.apply` records the bytes of the copy's `*.rej`
  files; on a non-zero exit, each `.rej` that is new or whose bytes changed is a target file (path without
  `.rej`) and its `@@` lines are the failing hunks; locale never matters, and `.rej` files the **Upstream** folder
  ships count only if git rewrote them. None means git refused the patch whole (file to change missing, file to
  create present, malformed, `..` path): the failure is git's stderr. `patch.apply` raises `PatchFailed(lines)`
  for the first failing file, listing the later ones as not tried.

- **Collect, then raise once**: `walk` catches `PatchFailed` per **Skill**, records it with the **Upstream**
  folder, skips that **Skill**'s scan (so nothing it reaches is queued), and goes on. After the BFS, before prose
  classification and warnings, any failures raise one `PatchError(SkillGraftError)` holding them as
  `(skill, upstream, lines)`; its message names, per **Skill**, the failures and "redo it against" and the
  **Upstream** folder. Any other `SkillGraftError` during the walk, once failures are collected, raises a
  `PatchError` holding them with that error's message last, so none is lost. The unused-key warnings are never
  computed, so none is misleading. `references.scan`'s warnings for a patched **Skill** name the **Upstream**
  path: `walk` replaces the copy's path prefix with it.

- **Config reads the patch files**: `Config.patches: dict[SkillId, list[PatchFile]]`, `PatchFile(path, data)`,
  `path` as written. Each path is resolved against the folder holding `skill-graft.toml`, `~` expanded, as path
  **Sources** are; the bytes are read at load, so a missing file is an error used or not, and lines `git apply`
  would skip as noise, losing a change silently, are rejected there, used or not, naming the file:
  `Binary files … differ`, `Only in …` and `GIT binary patch`. Duplicates under one key compare resolved paths.

- **Warnings**: `patch.unused(config, skills)`, called in `resolve.resolve` beside `rename.unused`:
  `[patches] "<key>" patches no skill in the hull`.

- **Lock and tree**: `lock.render` adds `upstream` (from `hull.upstream`) to every **Skill** and
  `patches` (from `hull.patches`, unsorted) to a patched one. `lock.tree`'s `node` appends `(patched)` after any
  `as <name>`.

- **Update**: `_previous` catches `PatchError` before `SkillGraftError`: "patches fail at the current refs". In a
  dry run, `update` catches `PatchError` from the tips resolution, replaces "redo it against" and the **Upstream**
  folder for an **Upstream** folder under the temporary cache root with "run `update` without `--dry-run` to fetch
  the tip", and re-raises.

## Risks / Trade-offs

- [A patch with both rejected hunks and a whole-file error reports only the hunks] → it still fails, and once its
  hunks are fixed the next run shows git's message; parsing git's localized stderr for the mix is not worth it.
- [Symlinks are copied as files before patching, so a git patch that edits a symlink as a link fails] → the copy
  matches what is vendored; such a patch is reported like any other failing one.
- \[The copy is owner-writable where the **Upstream** folder was not, so vendored modes may gain `u+w`\] → modes
  other than the exec bit are neither hashed nor deployed differently.
- \[A path **Source** edited between the copy and vendoring\] → vendoring reads the copy, so the build is
  consistent with what was scanned.
- \[Every existing lock gains `upstream`\] → one-time diff, noted in the proposal.

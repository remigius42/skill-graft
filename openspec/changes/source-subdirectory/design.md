# Design

## Context

Every command reads its **Sources** through `resolve.folders`, which maps each alias to a folder: a path
**Source**'s own folder, or `cache.checkout(alias, url, ref)` for a git one. `resolve.indexes` hands each folder to
`discovery.index(folder, confined)`. That index's `root` becomes `Hull.roots[alias]`, which `lock.render` uses to
write `upstream` as a relative path. `Hull.upstream` stays absolute, and `why` prints it. `update` calls `folders`
with the tips, so whatever `folders` checks also applies to `update`. The cache keys exports by URL and commit
alone.

## Goals / Non-Goals

**Goals:** narrow what `folders` returns for a git **Source** and check it there. The lock is the only output that
must say more.

**Non-Goals:** a sparse fetch or export of only the subdirectory; any change to the cache layout.

## Decisions

- **`GitSource.subdirectory: str | None`**, validated in `config._git_source`, kept as written. A field on the
  source, unlike `prefix` (`Config.prefixes`), because the code that reads a git **Source**'s tree needs it, and a
  path **Source** cannot have it. Validation is lexical, so a bad value fails before git runs: split on `/`, refuse
  empty, `.` and `..` segments, NUL and other control characters (a NUL would make the later file system call
  raise `ValueError`, which no caller catches), and an `.apm` segment followed by `skill-graft`. Discovery checks
  `paths.in_package` for every folder it descends into, but never for its walk root. A subdirectory inside a
  committed **Package** would therefore find nothing below it, yet would read a `SKILL.md` directly in it. Refusing
  the value says so at load instead of a silent empty or stray **Source**.
- **`folders` returns `export / subdirectory` after a check (`_subdirectory(alias, export, sub, ref)`).** It walks
  the segments from the export. Each must be the exact name of an entry in its parent folder (`os.scandir`), and
  that entry must be a directory and not a symlink (`is_dir(follow_symlinks=False)`). Comparing names, rather than
  calling `lstat` on the joined path, makes a case-insensitive file system refuse `PStack/skills` as Linux does, so
  the lock stays the same on every machine. Otherwise it raises
  `source 'cp': subdirectory 'pstack/skills' is not a folder at <sha>`, or `… runs through a symlink at <sha>`. The
  error always names the whole subdirectory as written, never only the segment that failed. Refusing symlinks
  outright is simpler than resolving and confining them, and a
  committed symlink as a plugin folder is far more likely a mistake than intent. Alternative: check inside
  `Cache.checkout`. Rejected: the export is the whole tree, shared by aliases with different subdirectories, so
  the cache has no business knowing about any one of them.
- **Discovery is confined to the subdirectory, not the export.** `discovery.index(folder, confined=True)` already
  takes its `root` from the folder it walks, so a link leaving the subdirectory is not followed, even one that
  stays inside the repository. That keeps "as if it were the repository root" literal, and keeps the other
  plugins' skills out, which is the point of the key. No discovery code changes.
- **The lock's `upstream` is relative to the repository root.** `Hull.roots[alias]`, which only `lock.render`
  reads, becomes the **Source**'s root, not the walked folder: the export for a git **Source**, the folder for a
  path one. `Index.root` stays the walked folder, as discovery needs it. `folders` keeps returning the walked
  folders, so its callers (`cli._resolve`, `edit`, `update._update`, `update._previous`, `resolve.known`) are
  unchanged. `resolve.resolve`, which has the config, derives each root from its folder: for a git **Source**
  with `subdirectory`, the folder's ancestor one level up per segment. It hands the roots to `hull.walk` beside
  the indexes, and the `Hull.roots` comment in `hull.py` says it is the **Source**'s root, not the walked folder.
  `lock.render` keeps `upstream.relative_to(root)` unchanged. That gives
  `pstack/skills/tdd`, or `plugins/chisel` for a skill at the subdirectory itself. Alternative: `lock.render` joins
  `subdirectory` with the path relative to the walked folder. Rejected: then both places must know that the root is
  not the root. Export joined with `upstream` is then the skill's folder for any reader, and graft-check needs no
  second key. The source table gains `subdirectory` when set. `version` stays 1: there are
  no users to migrate, and every lock written without a subdirectory is byte for byte as before.
- **`update` needs no code of its own.** `_update` prints each tip, then calls `resolve.folders(..., tips)`, which
  raises before any write, so a subdirectory gone at the tip exits non-zero with that error. Only when the
  current `ref` lacks the subdirectory and the tip has it does `_previous` meet the error. It catches it and prints
  "no previous hull to compare (the current refs do not resolve: …)", and the update goes on. A dry run reads
  tips from its temporary cache just as before.
- **`why` needs no change**: `Hull.upstream` is already the absolute folder inside the export, which now
  includes the subdirectory. A scenario in the tests pins that down.

## Risks / Trade-offs

- \[A subdirectory renamed upstream fails every `update` of that **Source**\] → The error names alias, subdirectory
  and tip sha; the user edits `subdirectory`, and since `ref` has not moved, `build` keeps working meanwhile.
- \[Two aliases on one URL with nested subdirectories (`a`, `a/b`) list the same **Skills** twice\] → Each is its own
  **Source** with its own **Skill IDs**; cross-source resolution reports the ambiguity it would for any two
  **Sources** sharing a name, and a **Bind** settles it. Not worth a check.
- \[A bad subdirectory in one **Source** fails `add`, `bind` and the other edits for a **Skill** of another\] →
  Already true of a missing `ref`: `folders` reads every **Source**, because a **Reference** may resolve in any.
  The error names the **Source** to fix.
- [A subdirectory that is a submodule fails as "not a folder"] → Submodules are skipped, so the export has no
  such folder. The error names the subdirectory and the commit, and `git ls-tree` there shows the gitlink. Rare
  enough not to need a message of its own.
- [A file system that normalizes Unicode names (HFS+ stores NFD) refuses a non-ASCII subdirectory written in NFC]
  → The exact-name comparison sees different bytes. APFS, macOS's default, keeps names as written. Known
  limitation; the error names the subdirectory.

## Migration Plan

None. Configs without `subdirectory` load, resolve and lock exactly as before.

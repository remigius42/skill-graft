# Proposal

## Why

Skills mostly live in other people's git repositories, but only path **Sources** work today. Git **Sources**
read at a fixed **Ref** make a build reproducible, and `update` moves the **Ref** on purpose instead of
silently.

## What Changes

- Config: a `[sources.<alias>]` table holds either `path` (unchanged) or `git` (a URL, scp-like address or
  absolute path; never relative), with optional `branch` and `ref`. `ref` is a full hex commit name. `git`,
  `branch` and `ref` stop being unsupported keys.
- Cache: one bare repository per git URL and one checkout per **Ref**, under `$XDG_CACHE_HOME/skill-graft/`
  (else `~/.cache/skill-graft/`), outside `~/.apm/skill-graft/`, in the remote's hash format (SHA-1 or
  SHA-256).
- `build`: reads each git **Source** at its **Ref**, fetching only when the **Ref** is missing from the cache,
  and never moves it. A git **Source** without `ref` is an error pointing to `update`.
- New `skill-graft update [alias…]`: fetches each git **Source**'s branch (default: the remote's default
  branch), resolves the **Entries** at the new tips, and only if that succeeds writes the tips into `ref` with
  `tomlkit`, keeping comments and formatting. Prints `<alias> <sha>` per source. Path sources are skipped;
  naming one is an error. `--dry-run` writes neither the TOML nor the cache.
- `init`'s commented template shows a git source too.
- Runtime dependency: `tomlkit`.

Out of scope: **References** and the **Hull**, the lock, **Renames**, **Binds**, **Patches**, the hull diff and
failing-patch output of `update`, cache pruning, submodules and LFS.

## Capabilities

### New Capabilities

- `git-sources`: fetching git **Sources** into the cache and reading them at their **Ref**.
- `update`: moving each git **Source**'s **Ref** to its branch tip.

### Modified Capabilities

- `config`: sources are path or git; `git`, `branch` and `ref` become supported.
- `init`: the template documents git sources.

## Impact

- New: `src/skill_graft/git.py`, `src/skill_graft/update.py`, tests for both.
- Changed: `config.py` (source kinds), `paths.py` (cache), `vendor.py` (source folder from the cache),
  `cli.py` (`update`), `init.py` (template), `tests/conftest.py` (`XDG_CACHE_HOME` unset, git repo helpers).
- `pyproject.toml` and `uv.lock` gain `tomlkit`.
- `docs/design.md`: `update` writes only when resolution succeeds, which overrides "writes, then resolves".
- Network: `build` fetches only a missing **Ref**; `update` fetches. Tests use local repositories only.

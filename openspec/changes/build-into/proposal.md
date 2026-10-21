# Proposal

## Why

The `graft-check` skill (ADR 0006, the **Check**) reads a built **Package**'s vendored **Skills** and lock, and so
far gets them by running `build --no-install` in place. That rewrites the live `.apm/skills/` and
`skill-graft.lock`: a committed project **Package** is left with a dirty working tree, and the user cannot just
look without changing anything. The **Check** needs a throwaway build.

## What Changes

- `skill-graft build --into <dir>` resolves and vendors as `build` does, but writes the vendored **Skills** to
  `<dir>/.apm/skills/<deployed name>/` and the lock to `<dir>/skill-graft.lock`, mirroring the **Package**, and
  never runs APM. The **Package**'s `.apm/skills/`, `skill-graft.lock` and `skill-graft.toml` stay byte-identical.
- The lock in `<dir>` holds the same bytes an in-place build would write; paths of project-scope path **Sources**
  stay relative to the **Package**, not to `<dir>`.
- `<dir>` must be an existing, empty folder (as `mktemp -d` makes), and must not lie in a **Package** (any
  `.apm/skill-graft` path), a path **Source**'s folder, or in or around the git cache. Otherwise `build` exits 1 before
  resolving. `build` never creates or deletes `<dir>` itself.
- `--into` with `--no-install` is a usage error (exit 2), as is `--into` without a value or with an empty one.
- After the `skill-graft: package: <path>` line, `build --into` prints `skill-graft: into: <absolute dir>`.
- The cache is written as usual: an uncached **Ref** is fetched.
- `build --help`, `README.md` and `docs/design.md` describe `--into`.

`--dry-run` was rejected as the name: on `update` it means "write nothing", while this writes, only elsewhere.
Copying the **Package** to a temporary folder instead was rejected: project-scope path **Sources** are stored
relative to the **Package**, discovery stops at the home folder, and changing `HOME` would break `~` paths and
refetch the cache.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build`: new requirements for building into a folder other than the **Package**, without APM; "Vendor
  entries", "Deploy through APM" and "Build resolves first" exempt `--into`.

## Impact

- `src/skill_graft/cli.py` (option, checks, wiring), `src/skill_graft/vendor.py` and `src/skill_graft/lock.py`
  (target folder as a parameter instead of always the **Package**'s).
- Tests in `tests/test_build.py`, `tests/test_git_build.py`, `tests/test_scope.py` and `tests/test_cli.py`.
- `README.md`, `docs/design.md`; `.cspell.yaml` if new words appear.
- The in-flight `graft-check` change switches to `build --into "$(mktemp -d)"` once this lands; it is not blocked
  meanwhile.

# Proposal

## Why

`mutmut-src` set up mutmut and left `pipeline/` with no unexplained survivor; its proposal named one change per layer
after it. This is `infra/`'s. A run of `skill_graft.infra.*` (on `206255fc`) leaves 201 mutants alive, 131 in `cache`:
no test notices the export writing symlinks first, `_safe` letting `..` through, or `fetch` dropping `--prune`, because
git's own fsck refuses a hostile tree before the export's second guard is reached, and the flags git is given are
checked only where they fail loudly.

## What Changes

- Every surviving mutant in `infra/` is killed by a test in its module's test file, dropped, marked equivalent, or is
  known noise (a message's wording, a change mypy refuses), as `mutmut-src` set out.
- Following `CONTRIBUTING.md`'s pragma rule, an equivalent mutant is dropped first: the redundant argument it shows goes
  (`check=False`, git's defaults, `init`'s `-q`), or the code is restructured, or the value is a module-level constant.
  41 of the 42 go so; 1 keeps a bare `# pragma: no mutate` alone on its line.
- `cache`'s second guards (`_safe`, the symlinks-last order, the check for an existing path) get tests that switch git's
  fsck off, so a hostile tree reaches them.
- A security guard no local remote shows (fsck of a blob fetch, `--` before a clone's URL, git's system config), or a
  flag that only saves work, is checked by recording the arguments git receives, as `test_cache.py` already does for
  `--refetch`; every other flag by its effect.
- `_read_blobs` checks each header's oid against the one asked for, so a misaligned parse fails instead of returning
  wrong bytes, with an error of its own; git's well-formed output never reaches it.
- `tests/infra/test_files.py` and `tests/infra/test_text.py` are new: `files` and `text` have no test file yet.
- No survivor is a bug: the source changes keep what a user sees.
- `CONTRIBUTING.md`'s baseline row for `infra`, and the total of survivors, get the new count.

## Capabilities

### New Capabilities

None: mutation testing binds the tests, not what a user sees.

### Modified Capabilities

None (`skip_specs: true`). A survivor that proves a bug in specified behavior adds its delta spec when found.

## Impact

- `src/skill_graft/infra/*.py`: redundant arguments removed, restructures and constants, the oid check, 1 pragma;
  nothing a user sees changes.
- `tests/infra/test_{cache,git,errors,apm}.py`; new `tests/infra/test_files.py`, `tests/infra/test_text.py`.
- `tests/test_mutation.py`: its selection test took `text`'s missing test file for the one to skip.
- `CONTRIBUTING.md`: the `infra` row of the baseline, and its total.

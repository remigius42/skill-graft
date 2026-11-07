# Tasks

One commit per task. Every mutmut run is `nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.infra.<module>*"`.
Groups 2 and 3 are test-first: each test fails against its mutant (`mutmut apply <mutant>`, reverted after) before it
passes on the code. Per task there: first rerun the module, as numbers shift; verify the rerun leaves only message
wording and mutants mypy refuses, and `uv run pytest` passes. Counts are from `206255fc`; see `design.md` for each
survivor's kind.

## 1. Equivalent mutants dropped

- [x] 1.1 `refactor(infra): drop what mutmut's equivalent mutants show redundant`: the 15 removals and 23 restructures
  in `design.md` (redundant `check=False`, `"wb"`, `-p1`, `-`, `strict=True`, `--full-tree`, `--no-tags` in `fetch` and
  `_refetch` with a comment on `tagopt`, `-q` in `init`, and in `_fetch_blobs` only if a probe of its failure shows the
  same text without it; `.split()`, `accumulate`, tree tips without `--no-walk` and the docstrings that name it, files
  then symlinks, `XDG_CACHE_HOME` without a default, `_pin` through `_has_commit`, and module-level constants for
  `git.run`'s locale, `_tree`'s hash length, the codec name and a swallowed check's context); verify `uv run pytest`
  passes before any new test. Each later task's module rerun shows those mutants gone

## 2. `cache` (131: 74 to kill)

- [ ] 2.1 The export: `_safe`, the symlinks-last order and the existing-path check with `git.FSCK` off; tab in a tree
  path; subdirectories `a*` and `--name-only`; mode `0o755`; two files; `_read_blobs` checking each header's oid, with
  an error of its own; a sibling blob left unfetched; the tips `_missing` lists from, recorded
- [ ] 2.2 Fetching: `fetch`'s `--prune`; `-q` in `fetch` and `_refetch` (a ref lock fails them after `From …`);
  `_clone`'s reference, `--no-tags`, `-q`, and `--` recorded; `_fetch_blobs`'s `origin` against a global
  `branch.main.remote`, its `--no-tags` (no tag in the overlay), and its `-q` if 1.1 kept it; `_refetch`'s refspec and
  git before 2.36; `git.FSCK` and `--recurse-submodules=no` on the blob fetch and refetch, recorded; the overlay's
  `--local`, `extensions.partialclone` (set by the test) and a space in the source path; `_pin` writing no ref when its
  pin exists, recorded
- [ ] 2.3 Housekeeping: `prune`'s boundary, `break` and unremovable leftover; `_build`'s cleanup; `_temporary`'s `.tmp`;
  `key`'s trailing `X`; a dry-run checkout of a subdirectory

## 3. The other modules

- [ ] 3.1 `git` (32: 17 to kill): `run` without `repo` (no `--git-dir`, git's own lazy fetch), non-UTF-8 stderr, the
  subcommand past options; `apply`'s `--whitespace=nowarn`, its `XDG_CONFIG_HOME`, its environment recorded, non-UTF-8
  stderr
- [ ] 3.2 `errors` (13): `flush_stdout` suppressing a bare `ValueError` and a bare `OSError` from `_discard`; a failed
  flush of a real pipe pointing stdout's descriptor at `os.devnull`
- [ ] 3.3 `files` (7) and `text` (10), new `tests/infra/test_files.py` and `test_text.py`: `atomic_write`'s temporary
  file beside its target; `text.ranges` called directly; pragmas on `atomic_write`'s `delete=False` and `os.umask(0)`
- [ ] 3.4 `apm` (7): `registered` with an item starting `X/`

## 4. The baseline

- [ ] 4.1 Rerun `skill_graft.infra.*`; the `infra` row of `CONTRIBUTING.md`'s baseline to its new count, triaged as
  known noise; verify only wording and mypy-refused mutants survive, and the markdown hooks pass

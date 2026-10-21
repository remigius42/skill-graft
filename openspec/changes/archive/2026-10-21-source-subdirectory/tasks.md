# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic git **Sources** in the test. `subdirectory` stays an unsupported source key until task 1.1 honors it in
full (read, checked, locked), so no commit accepts intent it ignores or mishandles.

## 1. Subdirectory

- [x] 1.1 `subdirectory` end to end. `config.py`: a supported key beside `git` only, a string validated
  lexically, into `GitSource.subdirectory`. `resolve.folders`: returns `export / subdirectory` after the
  exact-name walk, which fails naming the alias, the whole subdirectory and the commit when it is missing, not a
  folder, or runs through a symlink. `Hull.roots`: each **Source**'s root, the export for a git one, derived in
  `resolve.resolve` and passed to `hull.walk`, with its comment in `hull.py` updated, so `lock.render` is unchanged
  but for the source table's `subdirectory`. Verify the scenarios in the delta specs:
  config (subdirectory-not-a-string, subdirectory-key, subdirectory-on-a-path-source, valid-subdirectory,
  subdirectory-leaving-the-repository, control-character, subdirectory-into-a-package), git-sources
  (one-plugin-of-many, skill-outside-the-subdirectory, link-out-of-the-subdirectory, skill-at-the-subdirectory,
  missing-at-ref for `resolve` and `build`, a-file-not-a-folder, symlinked-subdirectory, shared-export, and the
  modified requirement's scenarios; case-differs only by the exact-name comparison, since Linux refuses another
  case either way and no test there can tell), resolve (subdirectory-recorded,
  upstream-under-a-subdirectory), update (subdirectory-gone-upstream, also with `--dry-run`). Also: `why` on a
  subdirectory **Source**'s skill prints an `upstream:` folder ending in `pstack/skills/tdd`. Every existing test
  passes, and a lock without `subdirectory` is byte for byte unchanged.

## 2. Docs

- [x] 2.1 `init.py`'s template gains a commented `subdirectory = "skills"` line under `[sources.mp]`, marked
  optional: read only this folder of the repository. `README.md`'s config section and `docs/design.md` (the TOML
  example, the `resolve` and `update` bullets, the lock paragraph under Feedback) document the key, its
  missing-at-ref error and `upstream` relative to the repository root. Verify: the init test that reads the
  template still passes, the documented TOML examples parse through `config.parse`, and
  `pre-commit run --all-files` is green.

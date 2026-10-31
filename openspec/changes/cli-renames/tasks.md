# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit, its seams confirmed first. Before the archive,
`git grep -niE 'build|built' -- . ':!docs/adr' ':!openspec/changes/archive'`,
`git grep -nE -- '--no-install|--diff($|[^-])' -- . ':!docs/adr' ':!openspec/changes/archive'` list every hit left;
check each by hand. Outside released `CHANGELOG.md` sections and the Upgrading entry, none may name the command,
`--no-install` or `--diff`, or mean vendoring. What stays: what the design keeps (the tagline "skill-graft builds a
user's agent skills", the top-level help's "Build your agent skills", `[build-system]` and `uv_build`, `cache._build`,
0.3.0's first line of a Deployed diff in `review.py` and the tests, the scenario headers task 6.1 renames), and "built"
or "rebuilt" in the sense of made ("built before any write", "built in the test", "built-in", "build-tool"), left as
written.

## 1. Options spelled in full

- [x] 1.1 `allow_abbrev=False` on `_Command` in `cli.py`, which the top-level parser and every command's parser are.
  Tests in `tests/cli/test_cli.py` for "Options spelled in full" (`update --dry` exits 2 naming `--dry` before the
  **Package** is looked for; `update --dry-run` runs); verify the tests fail first, then pass, and `pytest` is green.
  README.md's Commands section says options are taken only spelled in full

## 2. `build` becomes `deploy`

- [x] 2.1 `git mv` `commands/build.py` → `commands/deploy.py` with `build()` → `deploy()`,
  `tests/commands/test_build.py` → `test_deploy.py`, `tests/cli/test_git_build.py` → `test_git_deploy.py`, and
  `conftest.resolve_and_build` → `resolve_and_deploy` and `conftest.build` → `deploy`, in every test file that imports
  either (`git grep -nE 'resolve_and_build|^\s+build,|import .*\bbuild\b' tests`), and `vendored()`'s "the last build";
  the command `deploy` in `cli.py` (parser, help and description, dispatch), the "Never builds." of `add`, `remove`,
  `rename`, `bind` and `unbind`'s descriptions as "Never deploys.", and `scope.WRITERS`; the refusal hint
  `run skill-graft resolve to accept it, then deploy`; every test that runs `build` runs `deploy`, its names and
  docstrings too. Tests first: "Former names refused: Old command" (`build` exits 2 naming `build` and listing `deploy`)
  and "Help on every command" listing `deploy`, in `tests/cli/test_cli.py`; verify they fail, then pass, with `pytest`,
  `uv run mypy .` and `lint-imports` green
- [x] 2.2 The other messages that name the command or mean vendoring: `init`'s config comment and its APM failure hint
  (`skill-graft resolve, then skill-graft deploy`), `config.py`'s overlap error and `rename.py`'s "changed while
  building" (vendoring), and the docstrings and comments in `explain.py`, `compute.py`, `discovery.py`, `transaction.py`
  and `deploy.py`. Tests first in `tests/commands/test_init_package.py` and `tests/pipeline/test_config.py` for the
  changed messages; verify they fail, then pass
- [x] 2.3 Docs for `deploy`: README.md (the Usage flow, the Commands intro sentence and the Deploying table, "A package
  for one project", "Checking a package"), `docs/design.md`, `docs/security.md`, and `CONTEXT.md`'s **Package** entry
  (`deploy --into`). Verify `pre-commit run --all-files`

## 3. `--no-install` becomes `--no-apm-install`

- [x] 3.1 `--no-apm-install` in `cli.py` (help: stop before running APM) and `deploy.deploy`'s parameter; `--into` with
  it a usage error naming both; every test using it; README's Deploying table (what `--no-apm-install` does) and
  `docs/design.md`. Tests first: "Former names refused: Old install option", "Deploy without running APM" and "Into
  never runs APM: With no-apm-install" in `tests/cli/test_cli.py` and `tests/commands/test_deploy.py`; verify they fail,
  then pass

## 4. `--diff` becomes `--diff-file`

- [x] 4.1 `--diff-file` in `cli._review_options` for `resolve`, `add`, `remove`, `rename`, `bind`, `unbind`, and in
  `_parser`'s own `--diff` of `update`, with `update`'s description (`update --dry-run --diff-file review.diff`) and
  `--expect` help; `review.py`'s errors (`--diff-file <file>: …`) and docstrings, the `review:` and `apply:` hints and
  the `--expect` error in `update.py`; the comments in `edit.py` and `resolve.py`. `review.FIRST` says "each Skill's
  text as deployed", naming no command, and `review.check_target` also takes a file starting with the line 0.3.0 wrote.
  Tests first: "Former names refused: Old diff option", and the scenarios of `update`, `edit` and `resolve` whose output
  or hint names the option, in `tests/commands/test_update.py`, `test_edit.py`, `test_resolve.py` and `test_review.py`
  (a file 0.3.0 wrote, starting with its first line, still overwritten); verify they fail, then pass
- [x] 4.2 Docs for `--diff-file`: README.md (the getting-started flow, the staging paragraph, "Writing a patch"),
  `docs/design.md`, `docs/security.md`, each command's `--help`. Verify `pre-commit run --all-files`
- [x] 4.3 `cli._diff_file_option` adds `--diff-file` to `update` and to `_review_options`, and `cli._ONLY_DIFF_FILE`
  holds "nothing but the --diff-file FILE" for both `--dry-run` helps. A refactor: every command's `--help` stays byte
  for byte; verify that, and `pytest`

## 5. graft-check

- [x] 5.1 `skills/graft-check/SKILL.md` (throwaway deploy, `skill-graft deploy --into <folder>`, advising
  `skill-graft deploy`, the description's "references its vendoring got wrong"), `reader.json` (`vendored`: as vendored,
  "a finding vendoring caused"), `evals/graft-check/run.sh` (`deploy --no-apm-install`; scenarios `deploy-fails`,
  `never-deployed`; the `project` helper's `built` mode as `deployed`, with its comments; the throwaway build comment as
  throwaway deploy; `advises_deploy` matching `skill-graft deploy(?! --into)`) and `evals/graft-check/README.md`. Verify
  `bash -n evals/graft-check/run.sh`, `pytest tests/cli/test_check.py`, `pre-commit run --all-files`, and the greps
  above; the eval itself runs only when asked
- [x] 5.2 `evals/graft-check/run.sh`: the `project` helper drops its `deployed` mode, whose `deploy --no-apm-install`
  repeated what `resolve`, run first, had already vendored; its callers and `evals/graft-check/README.md` with it.
  Verify `bash -n evals/graft-check/run.sh`; the eval itself runs only when asked

## 6. Archive

- [ ] 6.1 In the archive commit: in `CHANGELOG.md`'s `[Unreleased]`, every `build` that names the command as it works in
  this release becomes `deploy`, and the Added entry for the edits' and `resolve`'s new option names it `--diff-file`;
  the Upgrading entry's runs made under 0.3.0 ("after its last `build`") keep `build`. Under `### Changed` this entry:
  "**BREAKING**: `build` is now `deploy`, its `--no-install` is `--no-apm-install`, and `update --diff <file>` is
  `update --diff-file <file>`; the old names exit 2. `deploy --into <dir>` is what `build --into <dir>` was. Options are
  no longer accepted abbreviated: `--dry` for `--dry-run` exits 2. Upgrade skill-graft first, then update its **Source**
  (`skill-graft update skill-graft` under `init`'s alias) and run `skill-graft deploy`: a graft-check vendored before
  this release runs `build --into` and ends with an error, and the new one runs `deploy --into`, which an older
  skill-graft refuses". Under `### Changed` also: "A **Deployed diff**'s first line names no command; a `review.diff`
  0.3.0 wrote is still overwritten". Then in the main specs: check the archive retired `openspec/specs/build/`
  (`retire_capabilities` in `.openspec.yaml`); rename to their `deploy` names the scenario headers the MODIFIED blocks
  kept (`check`: Build fails, Added but not built, Never built, Nothing to build; `cli`: Build; `hidden-characters`:
  Build into a folder; `patches`: Build writes nothing; `resolve`: Resolve and build agree, Build announces suggestions,
  Build into a folder announces none, Resolve and build agree with patches; `scope`: Project build, Build names the
  package); reword the Purpose of `check` ("a vendored **Package**") and `git-sources` ("so vendoring is the same
  wherever"). Verify `git grep -niE '#### Scenario:.*(build|built)' openspec/specs` prints nothing,
  `openspec validate --specs --strict` and `pre-commit run --all-files`

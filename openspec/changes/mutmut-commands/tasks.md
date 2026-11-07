# Tasks

One commit per task. Every mutmut run is `nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.commands.<module>*"`.
Groups 2 and 3 are test-first: each test fails against its mutant (`mutmut apply <mutant>`, reverted after), or for the
bug on the code, before it passes. Per task there: first rerun the module, as numbers shift; verify the rerun leaves
only known noise (wording, mypy refusals, import-time code) and the marked equivalents, and `uv run pytest` passes.
Counts are from `afa64801`; see `design.md` for each survivor's kind.

## 1. Refactors: equivalent mutants dropped or marked, `dry_cache` extracted

- [x] 1.1 `refactor(commands): drop what mutmut's equivalent mutants show redundant`: the `dry_run` and `project`
  defaults, `resolving`'s `checked` (its test and callers with it), `_undo_into`'s `missing_ok`; `explain.repository`'s
  regex as `_UNSAFE_URL`, a target in `mutation/targets.py` (`explain` in its `MODULES`), its return without a host and
  its segment check; `_path_url` without `safe=''`; `fetch_hint` by `zip` with the last line paired with none;
  `vendored` through `config.split_id`; `_tip`'s calls through `_ls_remote`; `update`'s target and diff as one value;
  verify `uv run pytest` passes before any new test (the harness's survivors on the new target are task 3.2's)
- [x] 1.2 `refactor(commands): one dry-run cache, review.dry_cache`: `dry_cache(stack) -> Cache`, its `root` the folder;
  `Run.__init__` and `update.update` call it; verify `uv run pytest` passes
- [x] 1.3 `refactor(commands): mark mutmut's equivalent mutants`: the 2 pragmas in `design.md` (`Run.text` declared on
  its class instead), each expression alone on its line with its reason above; verify `ruff format` leaves each pragma
  on its line, and the module reruns no longer list them

## 2. The bug

- [x] 2.1 `fix(update): a remote holding only tags names no default branch`: `update` against a remote with a tag and an
  unborn `HEAD` fails naming the alias and suggesting a `branch` key; `_tip` asks `_ls_remote` for heads and tags, not
  heads only; an empty remote still says it has no commits

## 3. Survivors killed

- [x] 3.1 `review` (22, with `update`'s 3 in `dry_cache`): `dry_cache`'s root name, removal and fallback cache;
  `vendored`'s malformed and partial locks; `fetch_hint`'s two hidden lines, and the other errors it keeps; `running`'s
  failing dry run without a hint
- [x] 3.2 `explain` (15): `tree_lines`' prose edges; `repository`'s port; `repositories`' skipped sources and non-forge
  URL; `link`'s fragment decoded and compared with level-9 compression on the same machine; `mermaid`'s `"`, given a
  `Repository` whose name holds one, as no `tree` input does; then `uv run python -m mutation explain._UNSAFE_URL`, each
  survivor killed by a test (a URL holding `\x7f`, for one) or listed in `mutation/equivalent.toml` with its reason,
  until it exits 0
- [x] 3.3 `deploy` (13): `deploy --into` failing mid-stage, and mid-swap with `swap_back` failing, leaves `into` empty;
  `test_interrupted`, whose interrupt hit `resolve` and never reached `deploy`, removed; `started` annotated, so mypy
  refuses its equivalent `None` mutant
- [x] 3.4 `edit` (12): each edit's dry-run hint; `bind` and `unbind` with `--diff-file`; `remove` without `entries`
- [x] 3.5 `vet` (9): `vet --into`'s nested file and modes; an unremovable alias folder (`needs_permissions`); `!` and
  `~` in a file name
- [x] 3.6 `update` (1 more), `transaction` (3), `resolve`, `init_package`, `scope` (1 each): `update`'s hint with two
  aliases; `pending` with no lock; restore of a file already gone; `resolve`'s kept diff; `init --project`'s listed
  failure; `scope.of` without `PWD`

## 4. The baseline

- [ ] 4.1 Rerun `skill_graft.commands.*`; the `commands` row of `CONTRIBUTING.md`'s baseline to its new count, triaged
  as known noise and marked equivalents, and the total of survivors with it; verify the markdown hooks pass

# Proposal

## Why

`mutmut-src` set up mutmut and left `pipeline/` with no unexplained survivor; `mutmut-infra` did the same for `infra/`.
This is `commands/`'s change. A run of `skill_graft.commands.*` (on `afa64801`) leaves 191 mutants alive, the baseline's
count: no test notices `deploy --into` leaving its folder full after a failure, `vet --into` writing every file
executable, `tree` expanding a skill under a prose line, or the dry-run hint of `remove` naming another command. One
survivor is a bug: `update` tells a remote holding only tags that it has no commits.

## What Changes

- Every surviving mutant in `commands/` is killed by a test in its module's test file, dropped, marked equivalent, or is
  known noise (a message's wording, a change mypy refuses, code that runs only at import), as `CONTRIBUTING.md`'s
  Mutation testing section sets out.
- Following its pragma rule, an equivalent mutant is dropped first: 30 go by removing a redundancy or restructuring
  (unused defaults of `dry_run` and `project`, `resolving`'s `checked`, `Run`'s initial `text`, `explain`'s `repository`
  and `_path_url`, `review.fetch_hint`'s look-ahead, `review.vendored` splitting a skill ID through `config.split_id`,
  `update._tip`'s three `ls-remote` calls through one that builds their arguments as a list, `update`'s target and diff
  as one value); 2 keep a bare `# pragma: no mutate` alone on their line; `deploy`'s `started` is annotated, so mypy
  refuses its one.
- `explain.repository`'s regex, which keeps a token in a URL's query out of the mermaid.live link, moves to a
  module-level constant, out of mutmut's reach, and becomes a target of the regex harness, `mutation/`.
- A dry run's temporary cache, built twice today (`review.Run`, `update.update`), is built by one public function in
  `review`, `dry_cache`, so its folder name and its fallback to the real cache are tested once.
- The bug: `update` without `branch`, against a remote whose `HEAD` names no branch but which holds tags, says the
  remote names no default branch and suggests a `branch` key, as the spec's **No default branch** scenario says, not
  that it has no commits yet; it asks the remote for heads and tags, not heads only. Its `Fixed` entry comes with the
  archive commit.
- `CONTRIBUTING.md`'s baseline row for `commands`, and the total of survivors, get the new count.

## Capabilities

### New Capabilities

None: mutation testing binds the tests, not what a user sees.

### Modified Capabilities

None (`skip_specs: true`): the bug's fix brings `update` in line with its existing **No default branch** scenario.

## Impact

- `src/skill_graft/commands/*.py`: removed defaults and parameter, restructures, one shared function in `review`, 2
  pragmas, `update._tip`'s fix.
- `tests/commands/test_{review,explain,deploy,edit,vet,update,transaction,resolve,init_package,scope}.py`; tests that
  pass `checked=` to `transaction.resolving`, or rely on a removed default, change with it.
- `mutation/targets.py`: `explain`'s URL regex; `mutation/equivalent.toml` if the harness finds an equivalent mutant of
  it.
- `CHANGELOG.md`: a `Fixed` entry, at archive.
- `CONTRIBUTING.md`: the `commands` row of the baseline, and its total.

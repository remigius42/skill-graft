# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit.

## 1. The option

Tests fake the installed distribution with `monkeypatch` on `importlib.metadata` through `cli`'s import of it, so they
hold whatever installer ran the suite.

- [ ] 1.1 Add `--version` to the top-level parser as a custom action printing `skill-graft <version>` from
  `importlib.metadata`, computed only when given; tests in `tests/cli/test_cli.py`: the cli spec's "Release", "Broken
  package" and "Listed in help" scenarios, `skill-graft unknown` for a missing distribution, and another command still
  running when the distribution is missing; verify they pass
- [ ] 1.2 Follow the version with `(<revision> @ <commit>)` or `(<commit>)` from `direct_url.json`'s `vcs_info`;
  tests: "Git install without a revision", "Git install at a branch", "Git install at a commit", "Other version
  control", a ref holding `%` printed as is, and the version only for a `direct_url.json` that is missing, not JSON,
  not an object, holds `dir_info` instead of `vcs_info`, or a `vcs_info` without `commit_id`; verify they pass

## 2. Docs

- [ ] 2.1 In `.github/ISSUE_TEMPLATE/bug_report.md`, ask for the output of `skill-graft --version` instead of a tag or
  commit; in `README.md`'s Installation section, say `skill-graft --version` names what is installed, with the commit
  for a git install; verify `pre-commit run --all-files`

## 3. Changelog

- [ ] 3.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`, `### Added`: `skill-graft --version` prints the
  version, and for a git install the commit. Per `AGENTS.md` it lands in the archive commit; check the box there;
  verify `pre-commit run --all-files`

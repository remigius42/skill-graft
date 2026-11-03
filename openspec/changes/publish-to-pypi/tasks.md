# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor where it changes code, one commit.
`pre-commit run --all-files` stays green, and every commit passes `pytest`.

## 1. README installs from PyPI

The README change comes first: the `skill-graft==` pair of 1.2 fails on a README without a `==` line.

- [x] 1.1 `README.md` Installation: drop "It is not on PyPI"; lead with the four `skill-graft==<version>` lines of
  design.md; below them the repository URL lines, each `@v<version>`, with the signed-tag check, as the way to install
  exactly the signed commit, and the `main` install as the sentence it is now, not a URL line. Every relative link
  outside the README (`docs/security.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, the badge's `pyproject.toml`)
  becomes its `https://github.com/remigius42/skill-graft/blob/main/…` URL. Verify: `check-pins` passes; mdformat and
  markdownlint pass; `grep -nP '\]\((?!https?://|#)' README.md` finds nothing; each PyPI line resolves, by
  `uv pip install --dry-run skill-graft==0.4.0` once 0.4.0 is on PyPI (after 4.1), else by reading
- [x] 1.2 `scripts/check_pins.py`: a pair of its own, `skill-graft==`, each README `skill-graft==<version>` against
  `pyproject.toml`'s version, beside the `@v` pair, renamed `skill-graft@v`. Tests in `tests/test_check_pins.py`: the
  synthetic README gains a `uv tool install skill-graft==0.3.0` line; a README whose `==` version differs from
  `pyproject.toml`'s fails naming `skill-graft==` and both versions, while its `@v` URLs still match; a README with no
  `==` line fails with `skill-graft==: not found in README.md`, one with no `@v` with
  `skill-graft@v: not found in README.md`. CONTRIBUTING's Tooling list names the new pair. Verify red, then green;
  `check-pins` passes on the repository

## 2. Publish workflow

- [x] 2.1 `check-github-workflows` hook from the `check-jsonschema` repo in `.pre-commit-config.yaml`; then
  `pre-commit run --all-files`, as a hook's config changed. Verify: it passes on `ci.yml`, and fails on a scratch copy
  of `ci.yml` with `runs-on` removed
- [x] 2.2 `.github/workflows/publish.yml` as design.md describes: triggers `push` of tags `v[0-9]+.[0-9]+.[0-9]+` and
  `workflow_dispatch` with a required `tag` input, passed to steps only through `env:` and refused unless
  `v<digits>.<digits>.<digits>`; job `build` (`contents: read`) checks out `refs/tags/<tag>`, fetches its tag object
  with `git fetch --force`, verifies it against the README's `namespaces="git"` line with `git verify-tag`, checks
  `HEAD` is `<tag>^{commit}`, compares the tag minus `v` with `uv version --short`, failing with a message that names
  both, runs `uv build` and uploads `dist/`; job `publish` (`id-token: write`, environment `pypi`) downloads `dist/` and
  runs `pypa/gh-action-pypi-publish`; a `concurrency` group per tag, `cancel-in-progress: false`. Every action pinned by
  SHA with its version in a comment, `persist-credentials: false`, as in `ci.yml`. Verify: `check-github-workflows`
  passes; no `run:` script holds `${{ inputs`; the `build` job's steps, run by hand in a scratch clone at `v0.4.0`,
  pass, after checking out the tag as `actions/checkout` does, a lightweight tag on the commit, so the `--force` fetch
  is what makes them pass; and fail: at `v0.4.0` replaced by a lightweight, unsigned tag at the same commit, naming the
  signature; at `v0.4.0` re-signed by a scratch key, naming the signature; with `HEAD` at another commit than the tag;
  at a signed scratch tag `v9.9.9` naming `9.9.9` and `0.4.0`; and for the input `v0.4.0;true`, before any checkout;
  `uv build` there yields `skill_graft-0.4.0.tar.gz` and `skill_graft-0.4.0-py3-none-any.whl`, whose files under
  `skill_graft/` match `git ls-tree -r v0.4.0 src/skill_graft`

## 3. Releasing

- [x] 3.1 `CONTRIBUTING.md` Releasing: the README step also replaces each `==<previous version>`; after the atomic push,
  approve the `publish` job of the `publish.yml` run for the tag once its `build` job passed, and watch it; if it fails,
  fix on main and, once PyPI shows the version is not there, start it by hand for that tag; the "wrong tag" paragraph
  says a version on PyPI cannot be removed and reused, only yanked, followed by a patch release. A one-time setup
  paragraph: the pending publisher and the `pypi` environment, limited to tags `v*.*.*` and the branch `main`, the
  maintainer its required reviewer, "Prevent self-review" off. Verify: each command in the section runs as written in a
  scratch clone where it does not push, and mdformat passes

## 4. Claim the name

- [ ] 4.1 After the merge to main, and with the user doing the pypi.org and GitHub settings of design.md's Migration
  Plan, and right after them, as a pending publisher does not reserve the name: start `publish.yml` with `tag: v0.4.0`.
  Verify: its `publish` job waits for approval and uploads nothing before; once the user approves, the run passes; PyPI
  lists `skill-graft` 0.4.0 with an attestation for each file; `uv tool install skill-graft==0.4.0` with `HOME` a
  scratch directory installs, and `skill-graft --version` prints `skill-graft 0.4.0`

# Design

## Context

`ci.yml` has two jobs, `pre-commit` and `commitlint`, using `actions/checkout@v7.0.1` and
`astral-sh/setup-uv@v10.2.0`. Neither job writes to the repository or calls the GitHub API. No version is tagged;
`pyproject.toml` says `0.1.0`. Fifteen OpenSpec changes are archived; `layer-packages` is a refactor, and
`graft-check` ships a skill in this repository rather than CLI behavior.

## Goals / Non-Goals

**Goals:**

- The workflow's token can only read, and a moved tag cannot change what CI runs.
- A user can read what skill-graft does differently from one release to the next, without reading OpenSpec.

**Non-Goals:**

- Keeping the pinned SHAs current (Dependabot or Renovate): a later change.
- Generating the changelog from commits.
- Changing hooks, `default_install_hook_types`, or anything a contributor runs.

## Decisions

- **Permissions at the top level, `contents: read` only.** Both jobs only check out. Per-job blocks would repeat it;
  a job that ever needs more adds its own block. Alternative: no block, relying on the repository's default token
  setting. Rejected: that setting is invisible in the repository and may be read-write.
- **Pin by full SHA, the tag in a comment** (`uses: actions/checkout@<40 hex> # v7.0.1`). Look the SHA up with
  `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, which peels an annotated tag to its commit. The comment
  keeps the version readable and is the format Dependabot updates later. The `npx` versions in the `commitlint` job
  are already exact and stay.
- **Changelog by what users notice, not by change.** An entry names a command, config key or behavior in the
  README's words, not an OpenSpec change. Changes that refine one feature merge into one entry (`resolve-hull`,
  `reference-detection` and `early-entry-clash` describe how **References** and the **Hull** work). Refactors and
  internal tooling get none (`layer-packages`, this change). `graft-check` gets one: users install that skill.
  Sections are Keep a Changelog's (`Added`, `Changed`, `Fixed`, …); before a first release nearly all is `Added`.
- **The changelog rule lives in `AGENTS.md` (Workflow)**, next to "propose, wait, apply": the archive commit adds the
  entry, so the changelog never lags the main specs. Alternative: write entries at release time. Rejected: by then
  nobody remembers what a change meant to a user.
- **`CONTRIBUTING.md` links rather than repeats.** It holds what a person needs before the first commit: `git` and
  `uv` (which fetches Python 3.11 for the oldest-Python hook; pre-commit sets up the Node hooks itself), `uv sync`,
  `uv run pre-commit install --hook-type pre-commit --hook-type commit-msg`, the OpenSpec loop in three lines, and
  that evals are opt-in and billed. Rules (Git, Python, tests) stay in `AGENTS.md`, terms in `CONTEXT.md`; the file
  links both, and opens with a link to the README's `## Engagement` section, so a contributor reads it first.
- **The engagement note in the README, copied from `claude-cloud-test`**, the only sibling with one: "This is a
  personal exploration project with best-effort maintenance. Responses to issues or pull requests may be slow, and
  changes that don't align with the project's direction are unlikely to merge." The same words across repositories
  read as one policy. It goes last in the README, where readers look for project status, and the README is what
  GitHub shows; `CONTRIBUTING.md` only links it.

## Risks / Trade-offs

- [Pinned SHAs stop receiving fixes] → named as a non-goal; the tag comment shows how old each pin is.
- [A SHA copied wrong breaks CI] → CI runs only on `main` and pull requests, so the branch cannot prove it. Each
  SHA is checked to be the commit its tag names (`gh api …/commits/<tag>`) and the workflow parsed (`check-yaml`);
  the first push to `main` confirms it.
- [The seeded changelog misstates a feature] → each entry is checked against the README and the main specs, not
  only the archived proposal, since later changes refined several of them.

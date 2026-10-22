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
- **`CONTRIBUTING.md` is `docs/development.md`, moved** (`git mv`, so history follows), not a second guide: GitHub
  links `CONTRIBUTING.md` from issues and pull requests, and two setup guides would drift. It keeps what a person
  needs before the first commit (setup, checks, evals) and adds the OpenSpec loop in three lines. Rules (Git,
  Python, tests) stay in `AGENTS.md`, terms in `CONTEXT.md`; it links both rather than repeat them.
- **README order: identification, evaluation, usage, reference, contributing.** Title with link and badges, then a
  copyright line; the existing what-and-why paragraphs and `Status: beta.`; `## Installation` with its
  prerequisites; `## Usage`; then `## Commands`, `## Config`, and the topic sections (`A package for one project`,
  `Checking a package`, `Writing a patch`) as reference; `## Contributing` last.
- **`## Usage` is one scenario, start to finish**, every step a command or a config edit the reader can copy: `init`;
  a git source added to `skill-graft.toml` (`[sources.mp]` with `git = "https://github.com/mattpocock/skills.git"`,
  as the config example uses); `skill-graft update mp` to set its `ref`; `skill-graft add mp/tdd`;
  `skill-graft tree` to see the hull; `skill-graft build`. Its prerequisites are Installation's plus a harness folder
  APM deploys to. Variants (project scope, `--into`, renames, patches) are links to their sections, not more steps.
  The scenario is run as written against a temporary `HOME` before it is committed; if `mp/tdd` no longer exists
  upstream, another skill of that source takes its place.
- **`## Contributing`, not `## Engagement`**: readers scan for the GitHub convention, and it matches the file it
  links. It holds the issues link, the `CONTRIBUTING.md` link, and `claude-cloud-test`'s note verbatim: "This is a
  personal exploration project with best-effort maintenance. Responses to issues or pull requests may be slow, and
  changes that don't align with the project's direction are unlikely to merge." The same words across repositories
  read as one policy; that repository's heading stays as it is.

## Risks / Trade-offs

- [Pinned SHAs stop receiving fixes] → named as a non-goal; the tag comment shows how old each pin is.
- [A SHA copied wrong breaks CI] → CI runs only on `main` and pull requests, so the branch cannot prove it. Each
  SHA is checked to be the commit its tag names (`gh api …/commits/<tag>`) and the workflow parsed (`check-yaml`);
  the first push to `main` confirms it.
- [The seeded changelog misstates a feature] → each entry is checked against the README and the main specs, not
  only the archived proposal, since later changes refined several of them.

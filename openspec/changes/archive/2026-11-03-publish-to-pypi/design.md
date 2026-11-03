# Design

## Context

A release today is a signed tag `v<version>` plus a GitHub release (CONTRIBUTING.md, Releasing); users install from the
repository URL at that tag. The build backend is `uv_build`, and `src/skill_graft/` is the whole package. CI (`ci.yml`)
has read-only permissions and SHA-pinned actions that Dependabot bumps. `check-pins` already pairs the README's
`@v<version>` URLs with `pyproject.toml`'s version, but only where `@v` follows `skill-graft` or a backtick, so
`skill-graft==<version>` goes unchecked. `skill-graft --version` prints the version alone when `direct_url.json` holds
no `vcs_info`, which covers a PyPI install, so the CLI does not change.

## Goals / Non-Goals

**Goals:**

- Nothing reaches PyPI that was not built from a signed release tag at its own version.
- No PyPI credential exists outside PyPI and GitHub's OIDC exchange.

**Non-Goals:**

- Reproducible builds, or checking that PyPI's files match a local build.
- Replacing the GitHub release: it stays, with the changelog as notes.

## Decisions

- **A separate `publish.yml`, not a job in `ci.yml`.** PyPI's trusted publisher names one workflow file, and an
  `id-token: write` permission should exist only in the workflow that uploads. CI has already passed the release commit
  by the time it is tagged (Releasing, step 4), so the publish workflow does not run the tests again.
- **Two jobs.** `build` checks out the tag, verifies it, runs `uv build` and keeps `dist/` as an artifact, with
  `contents: read` only. `publish` downloads it and runs `pypa/gh-action-pypi-publish`, with `id-token: write`, in the
  `pypi` environment. The build step never holds the token. That action, not `uv publish`, because it generates and
  uploads the PEP 740 attestations; `uv publish` uploads them only if they already exist.
- **Triggers: `push` of tags matching `v[0-9]+.[0-9]+.[0-9]+`, so a tag such as `v1.0.0-rc1` starts no run, and
  `workflow_dispatch` with a `tag` input.** The manual start publishes a tag that already exists, 0.4.0 first. It runs
  `publish.yml` from main but builds the tag's tree, so the backfill does not need the workflow at `v0.4.0`. The input
  reaches the steps only through `env:`, never as `${{ inputs.tag }}` inside a `run:` script, so it cannot inject shell;
  the first step refuses one that is not `v<digits>.<digits>.<digits>`. A push run takes the tag from `github.ref_name`
  the same way. Checkout names `refs/tags/<tag>`, so a branch of the same name is never built. A `concurrency` group per
  tag, not cancelling, keeps a push run and a manual run of the same tag from uploading at once; the upload skips the
  files PyPI already holds, so a second run of a tag, by hand after a failure, completes an upload that stopped halfway
  and is harmless after a whole one.
- **Verify the tag against the README at that tag.** The job fetches the tag object with
  `git fetch --force origin refs/tags/<tag>:refs/tags/<tag>`: `actions/checkout` leaves a lightweight tag of that name
  on the commit, which a fetch without `--force` refuses to replace, and `git verify-tag` would then find no signature.
  It writes the README's `namespaces="git"` line to an allowed-signers file and runs `git verify-tag`. It then checks
  that `HEAD` is the verified tag's commit, so a tag moved between checkout and fetch fails rather than building other
  files than were verified. Then it compares the tag, minus `v`, with `uv version --short`. Taking the key from the
  README avoids a second copy of it to keep in step. The alternative, a committed `.github/allowed_signers` paired with
  the README by `check-pins`, adds a file and a pair to protect against something the environment's tag rule already
  covers (see Risks).
- **The `pypi` environment allows tags `v*.*.*` only, and requires the maintainer's approval.** GitHub checks the rule
  against the ref the run starts from: a push run's is the tag, and so is a re-run's, but a manual run's is `main`,
  where `publish.yml` lives (it does not exist at `v0.4.0`). So the branch rule `main` is added only while a manual run
  needs it, the backfill and a fix to the workflow itself, and removed after. The alternative, `main` allowed for good,
  would let any manual run reach the approval step; the signature check and the approval would still hold, but nothing
  needs it between releases. The pending publisher on pypi.org names the repository, `publish.yml` and `pypi`. An upload
  then needs a run of this workflow from a `v*.*.*` tag in this repository, or from `main` while it is allowed, building
  a signed release tag, and a click on "Approve and deploy" by the environment's one required reviewer, the maintainer.
  "Prevent self-review" stays off, or the only maintainer could never approve. A pushed tag alone, by mistake or by a
  leaked token, publishes nothing; the run waits, and expires after 30 days. The cost is one approval per release, which
  CONTRIBUTING's Releasing names as a step.
- **README: PyPI first.** The four install lines become `uv tool install skill-graft==<version>`,
  `pipx install --python python3.11 skill-graft==<version>`, `pip install skill-graft==<version>` and
  `pipenv install skill-graft==<version>`. The repository URL lines move below them, together with the signed-tag check,
  as the way to install exactly the signed commit. The unreleased `main` stays a sentence ("drop `@v<version>` from the
  URL"), not a line of its own, so every URL line names the release. The lines keep the version in them, as now, so the
  README at a tag installs that tag's release.
- **README links absolute, to `main`.** The README is the PyPI project page, where its relative links
  (`docs/security.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, the version badge's `pyproject.toml`) go nowhere.
  They become `https://github.com/remigius42/skill-graft/blob/main/…` URLs; anchors within the README stay relative.
  `main`, not `v<version>`: the vulnerability report path and the security notes should be the current ones for a reader
  of any release's page, and the badge already reads `main`. The cost: an anchor a later release renames breaks on an
  older release's page. The README's links to its own headings (`#cache` and the like) stay relative, though PyPI gives
  headings no ids, so on PyPI they go nowhere: making them absolute would send a GitHub reader off the page for each,
  and the PyPI page is the one read less.
- **`check-pins` pairs `skill-graft==<version>` as a pair of its own, named `skill-graft==`**, beside the `@v` pair,
  renamed `skill-graft@v`, both against `pyproject.toml`'s version. Pooled into one README side, a README that dropped
  every `==` line would still pass on its URLs; as its own pair, a missing form reports "not found", as any pair does,
  and the name says which form. The `@v` side matches the prose about `main` as well as the URL lines, so it checks that
  the README names the version with `@v` and that none names another, not that every URL line is pinned.
- **`check-github-workflows`** from the `check-jsonschema` repository the hooks already use, so a schema mistake in
  `publish.yml` fails at commit time and not at the first release.

## Risks / Trade-offs

- [Someone with write access pushes a tag signed with their own key, and changes the README's key in the same commit] →
  The signature check guards against mistakes, not against a rogue maintainer: such a person could also edit the
  workflow. Their tag passes the check and builds; what stops the upload is the required approval, together with
  two-factor authentication on GitHub and PyPI. The spec states the approval as a requirement of its own for that
  reason. The approval does not stop someone holding the maintainer's own GitHub session, who could approve too.
- [PyPI never takes the same version twice; a deleted version cannot be uploaded again] → A wrong release is yanked and
  followed by a patch release. CONTRIBUTING's "wrong tag nobody has installed" removal no longer applies once the
  version is on PyPI.
- [The 0.4.0 upload carries 0.4.0's README, which says "It is not on PyPI", on its PyPI page] → It is accurate about
  0.4.0 and is replaced on the page by the next release. So are its relative links, which go nowhere on that page until
  then. Releasing 0.4.1 straight after this change instead would leave the name open until then.
- [The publish run fails after the tag is pushed and the GitHub release exists] → The tag is fine. After an outage,
  re-run the failed jobs. After a fix to the workflow, which a re-run would not pick up, allow `main` for a moment and
  start it by hand for that tag.
- \[A pending publisher does not reserve the name: someone else can upload `skill-graft` before 0.4.0 goes up, and the
  pending publisher is then void\] → Migration steps 2 and 3 are done back to back, in one sitting; the window is
  minutes. Should the name be taken anyway, PEP 541 is the recourse, and the README keeps the git install.
- \[setup-uv installs the latest uv, so `uv version --short` or `uv build` could change under a release without a
  commit\] → Left unpinned, as in `ci.yml`, which runs that same latest uv on every push; nothing bumps a pin in
  `with: version`. A release build that breaks uploads nothing and is re-run once fixed.
- \[A manual run's attestation names `main` and main's commit, the workflow's, not the tag\] → The README says only that
  this repository's publish workflow built and uploaded each file; the tag tie is the signature check inside the run.

## Migration Plan

1. Merge this change into main.
1. On pypi.org: add a pending publisher for project `skill-graft`: owner `remigius42`, repository `skill-graft`,
   workflow `publish.yml`, environment `pypi`. In GitHub's repository settings: create the `pypi` environment,
   deployment limited to tags `v*.*.*` and, for the backfill only, the branch `main`, required reviewer the maintainer,
   "Prevent self-review" off.
1. Right after step 2, start `publish.yml` by hand with `tag: v0.4.0` and approve its `publish` job; check that PyPI
   shows 0.4.0 with attestations, and that `uv tool install skill-graft==0.4.0` in a scratch `HOME` installs it. Then
   remove the branch rule `main`.

Rollback: delete `publish.yml`. Releases already uploaded stay on PyPI and keep the name claimed.

# Design

## Context

See proposal.md for why. `docs/design.md` held three kinds of text: behavior the specs already state, behavior only it
stated, and how and why skill-graft works. The README held a reference and task guides side by side, and is the page
PyPI shows for each release.

## Goals / Non-Goals

**Goals:**

- One home per fact: behavior in the specs, mechanism and rationale in `docs/architecture.md`, tasks in `docs/howto.md`,
  reference in the README.
- A release's README leads to that release's docs.

**Non-Goals:**

- Rewriting the specs' existing requirements, or the ADRs.
- Pinning links to `SECURITY.md`, CONTRIBUTING.md and LICENSE, which say how the project works now, whatever release a
  reader runs.

## Decisions

- **Delete `docs/design.md`, keep no copy in `docs/archive/`.** Git holds every version, and `docs/architecture.md` says
  how to show the first and the last. A copy in the tree reads as current to people and agents, whom AGENTS.md sends to
  `docs/`. Alternative: archive the version from before the first OpenSpec change; rejected, as it would be stale on
  arrival.

- **What only `design.md` stated is sorted by whether a user sees it.** Six behaviors become spec deltas; mechanism (the
  transaction, the cache's pins, the patch environment) and rationale (the scan's classes, the link hosts) go to
  `docs/architecture.md`. The lone-surrogate rule follows from the decoding the spec already states, so it is rationale.
  So is writing `"` as `#quot;` in a Mermaid label: names, aliases and prefixes cannot hold a `"`, and a Skill tool
  reference is shown normalized, so no user can see it.

- **A synthetic config in the README, not the maintainer's.** A real config would name the repositories and refs one
  person trusts, and would not use every key the reference explains.

- **The README keeps its Cache section.** An error message (`infra/cache.py`) sends users to "Cache" in the README.

- **The README links the repository's files relatively; the build makes them absolute, naming the release.** GitHub
  resolves a relative link against the ref it shows, so main's README leads to main's docs and a tag's to its own, and
  none breaks between releases. PyPI resolves one against `pypi.org`, so the build rewrites each relative link and image
  to `blob/v<version>/` and `raw.githubusercontent.com/…/v<version>/`: hatch-fancy-pypi-readme's substitutions, with
  `$HFPR_VERSION`, the package's version. It is a hatchling metadata hook, and `uv_build` refuses dynamic metadata, so
  the build backend becomes hatchling; both are build requirements, not runtime ones. Same-page `#` links stay as they
  are, as do the absolute links to `SECURITY.md`, CONTRIBUTING.md and LICENSE on `main`. Alternatives: absolute
  `blob/main/` links, the common default, which show a user of an older release main's guides, open main's copy from a
  local preview or a branch's page, and 404 there for a file main lacks yet; hand-pinned `blob/v<version>/` links held
  by `check-pins` and raised in each release commit, which break until a release ships the files they name; rewriting in
  the publish workflow only, which keeps `uv_build` but makes a local build differ from the published one; a second
  README for PyPI, which doubles the text to keep in step.

- **The tag holds the relative links; only the built metadata names the release.** The tag's signature covers the tree,
  whose README is unchanged, so a clone matches what was signed and `publish.yml`'s key check reads the same file. The
  rewritten text lives only in the sdist's `PKG-INFO` and the wheel's `METADATA`, which PyPI's PEP 740 attestations
  cover; it follows from the tag's tree and version, so a build from the tag or the sdist repeats it.

- **One logo in the README, the full mark, 128 px, floated right.** The small mark is for sizes the full one blurs at,
  which the README is not; two would repeat it on one screen. On the right, the title, badges and pitch keep a straight
  left edge, also on a narrow screen. Markdown can neither size nor float an image, so `<img align="right">`, which
  GitHub and PyPI keep, and `img` joins MD033's allowed elements. Its `src` is relative, as the links are, and the build
  makes it absolute.

## Risks / Trade-offs

- [A relative link the substitutions do not match reaches PyPI broken] → they match each inline Markdown link without a
  title, and each `src`, that names no scheme and no `#` anchor; a test builds the wheel and fails on a relative link,
  reference definition, `src` or `href` left in its description, or a `blob/v` link naming another version or a missing
  file. An angle-bracket target, `](<docs/x.md>)`, comes out as `…/v<version>/<docs/x.md>`, which the test fails as a
  missing file.
- [The substitutions also rewrite a link inside a code span or fence, which the test misses when the file exists] → the
  README holds no such example; one added later would show on PyPI with the release's URL.
- [Offline, with hatchling not in uv's cache, the test cannot build the wheel and fails] → rare: uv keeps the build
  requirements once fetched.
- [A build from a commit between releases names a tag that lacks the files linked] → only a release is published, and
  its build names its own tag.
- [Spec deltas copy whole requirements, so a concurrent change to the same requirement conflicts] → none is in flight.
- \[`docs/apm-behavior.md` names APM 0.35.0 and no hook checks it\] → CONTRIBUTING.md's Tooling says to measure again
  when the `apm-cli` pin moves.

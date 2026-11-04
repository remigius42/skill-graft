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

- **What only `design.md` stated is sorted by whether a user sees it.** Seven behaviors become spec deltas; mechanism
  (the transaction, the cache's pins, the patch environment) and rationale (the scan's classes, the link hosts) go to
  `docs/architecture.md`. The lone-surrogate rule follows from the decoding the spec already states, so it is rationale.

- **A synthetic config in the README, not the maintainer's.** A real config would name the repositories and refs one
  person trusts, and would not use every key the reference explains.

- **The README keeps its Cache section.** An error message (`infra/cache.py`) sends users to "Cache" in the README.

- **The README's docs links name the release, `blob/v<version>/`, held by `check-pins`.** Each tag's README then leads
  to its own guides; the release commit raises them with the other pins. Alternatives: `blob/main/`, which shows a user
  of an older release main's guides; relative links, which PyPI does not resolve.

- **One logo in the README, the full mark, 128 px, floated right.** The small mark is for sizes the full one blurs at,
  which the README is not; two would repeat it on one screen. On the right, the title, badges and pitch keep a straight
  left edge, also on a narrow screen. Markdown can neither size nor float an image, so `<img align="right">`, which
  GitHub and PyPI keep, and `img` joins MD033's allowed elements. Its URL is absolute, which PyPI needs, and on `main`,
  not a tag: the logo does not change per release.

## Risks / Trade-offs

- \[Until the next release, `blob/v0.4.0/docs/howto.md` and `blob/v0.4.0/docs/README.md` do not exist\] → the branch
  merges right before a release, whose commit raises the links; `check-pins` checks the version, not that the file
  exists at that tag.
- [Spec deltas copy whole requirements, so a concurrent change to the same requirement conflicts] → none is in flight.
- \[`docs/apm-behavior.md` names APM 0.35.0 and no hook checks it\] → CONTRIBUTING.md's Tooling says to measure again
  when the `apm-cli` pin moves.

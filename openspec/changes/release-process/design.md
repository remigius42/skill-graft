# Design

## Context

`CHANGELOG.md` follows Keep a Changelog 1.1.0, all entries under `## [Unreleased]`, which has no link definition yet
(project-hygiene's design deferred it to the first tag). The version lives in `pyproject.toml` (`0.1.0`) and is
mirrored in `uv.lock`; the README's version badge reads `pyproject.toml` on `main`. CI runs on pushes to `main` and
on pull requests, not on tags. AGENTS.md forbids work on `main` and pushing without asking. `init`'s `apm.yml`
template also says `version: 0.1.0`: that is the version of the user's **Package** as APM sees it, not skill-graft's,
and a release leaves it alone.

## Goals / Non-Goals

**Goals:**

- A release is a fixed sequence anyone with push rights can repeat from `CONTRIBUTING.md` alone.
- The tag, the changelog heading, `pyproject.toml` and the GitHub release always name the same version.
- Only a commit CI passed on `main` is tagged.

**Non-Goals:**

- Automating any step (release-please, a tag-triggered workflow, generated notes).
- Signing tags, or attaching built wheels to the release.

## Decisions

- **Release commit on a branch, `release/v<version>`, fast-forwarded onto `main`.** AGENTS.md rules out committing on
  `main`, and a release is not an OpenSpec change, so it gets its own branch name rather than `feat/opsx-…`. The
  commit is `chore(release): <version>`, which commitlint's conventional config accepts. Alternative: let the archive
  commit of the last change carry the release. Rejected: a release often spans several changes and direct `fix:`
  commits, and the archive commit then means two things.
- **The release commit does all version edits at once.** It renames `## [Unreleased]` to `## [<version>] - <date>`
  (ISO date), adds an empty `## [Unreleased]` above it, and sets the link definitions at the end of the file:
  `[Unreleased]` comparing `v<version>...HEAD`, `[<version>]` comparing the previous tag with `v<version>`, or, for the
  first release, linking `releases/tag/v<version>`. It sets `version` in `pyproject.toml` and runs `uv lock` so
  `uv.lock` matches. Earlier link definitions stay as they are.
- **Version by Semantic Versioning, read from the changelog.** A `### Removed` entry, or a `### Changed` entry that
  breaks a config, command or lock a user already has, raises the major version (the minor before 1.0); a new
  `### Added` entry raises the minor (the patch before 1.0 only if nothing was added); only `### Fixed` raises the
  patch. The section names already sort the entries, so picking the version needs no other record.
- **Tag after CI, annotated, `v`-prefixed.** Once `main` is pushed and its CI run is green, tag the release commit
  with `git tag -a v<version> -m "skill-graft <version>"`, then push the tag alone. CI does not run on tags, so
  this order is what makes the tagged commit a checked one. `v` matches the sibling repositories and uv's and pip's
  `git+…@v<version>`. Annotated, so the tag records who tagged and when. Alternative: a lightweight tag. Rejected: it
  carries no date or tagger, and `git describe` skips it by default.
- **GitHub release notes are the changelog section, verbatim.** Publish with
  `gh release create v<version> --verify-tag --title "skill-graft <version>" --notes-file <file>`, the file holding
  the lines between that version's heading and the next `## [`. `--verify-tag` refuses to create a tag the release
  would otherwise make on the remote's default branch. Alternative: `--generate-notes`. Rejected: it lists pull
  requests and commits, not what a user sees.
- **README names the pattern, not a version.** Installation gains one sentence: append `@v<version>` to the git URL
  to install a release, listed under the repository's releases. A pinned `@v0.1.0` in every install line would go
  stale with the next release unless every release also edited the README.
- **`0.1.0` is cut in this change**, as its last task, by the steps it documents, so the documented steps are the
  ones that worked. `pyproject.toml` already says `0.1.0`; the release commit changes only `CHANGELOG.md`.

## Risks / Trade-offs

- [mdformat or markdownlint rewrites or rejects the link definitions] → run pre-commit on the release commit before
  tagging; markdownlint's MD053 accepts them since the headings use them as shortcut references.
- [A wrong tag is pushed] → before anyone installs it, `gh release delete v<version> --cleanup-tag --yes` removes
  release and tag; once someone may have installed it, leave it and release a fixed patch version instead.
- \[The release commit is tagged but a later commit on `main` is what CI checked\] → tag only when the release commit
  is the commit CI ran on, or an ancestor whose later commits only archive the change (`openspec/` moves).

## Migration Plan

For `0.1.0` the release commit is a task of this change, so it sits on `feat/opsx-release-process` in place of
`release/v0.1.0`. The archive commit must come after the tag, since tagging is a task. So: apply the documentation and release-commit
tasks on `feat/opsx-release-process`, fast-forward `main`, push, and wait for CI; tag and publish `0.1.0`; tick that
task and archive on the branch; fast-forward and push `main` again. Each push is confirmed with the user first.

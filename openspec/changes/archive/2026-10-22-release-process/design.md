# Design

## Context

`CHANGELOG.md` follows Keep a Changelog 1.1.0, all entries under `## [Unreleased]`, which has no link definition yet
(project-hygiene's design deferred it to the first tag). The version lives in `pyproject.toml` (`0.1.0`) and is mirrored
in `uv.lock`; the README's version badge reads `pyproject.toml` on `main`. CI runs on pushes to `main` and on pull
requests, not on other branches or tags; its commitlint job lints from `github.event.before`. AGENTS.md forbids work on
`main` and pushing without asking. `init`'s `apm.yml` template also says `version: 0.1.0`: that is the version of the
user's **Package** as APM sees it, not skill-graft's, and a release leaves it alone.

## Goals / Non-Goals

**Goals:**

- A release is a fixed sequence anyone with push rights can repeat from `CONTRIBUTING.md` alone.
- The tag, the changelog heading, `pyproject.toml` and the GitHub release always name the same version.
- Only a commit CI passed is tagged, and `main` never names a version CI has not passed.

**Non-Goals:**

- Automating any step (release-please, a tag-triggered workflow, generated notes).
- Signing tags, or attaching built wheels to the release.

## Decisions

- **Release commit on a branch, `release/v<version>`, fast-forwarded onto `main`.** AGENTS.md rules out committing on
  `main`, and a release is not an OpenSpec change, so it gets its own branch name rather than `feat/opsx-…`; AGENTS.md
  gains a line naming that exception and pointing to `CONTRIBUTING.md`. The commit is `chore(release): <version>`, which
  commitlint's conventional config accepts. Alternative: let the archive commit of the last change carry the release.
  Rejected: a release often spans several changes and direct `fix:` commits, and the archive commit then means two
  things.
- **The release commit does all version edits at once.** It renames `## [Unreleased]` to `## [<version>] - <date>` (ISO
  date), adds an empty `## [Unreleased]` above it, and sets the link definitions at the end of the file: `[Unreleased]`
  comparing `v<version>...HEAD`, `[<version>]` comparing the previous tag with `v<version>`, or, for the first release,
  linking `releases/tag/v<version>`. It sets `version` in `pyproject.toml` and runs `uv lock` so `uv.lock` matches.
  Earlier link definitions stay as they are. The date is the release commit's day, and the tag follows that day:
  release-please, semantic-release and cargo-release write it the same way, and a tag date could only be recorded by
  another commit after CI.
- **Version by Semantic Versioning, read from the changelog.** A breaking entry is one under `### Removed`, or under
  `### Changed` when a config, command or lock a user already has stops working as before. From 1.0: a breaking entry
  raises the major version, else an `### Added` or `### Deprecated` entry the minor, else (`### Fixed`, `### Security`,
  a `### Changed` that breaks nothing) the patch. Before 1.0: a breaking entry raises the minor, anything else the
  patch. The section names already sort the entries, so picking the version needs no other record.
- **CI before `main`: push the release branch, with CI running on `release/**`.** `ci.yml` adds `release/**` to its push
  branches, so pushing `release/v<version>` checks the release commit before `main` or the README's version badge names
  its version, without a pull request. Once the run is green, fast-forward `main` to the release commit and push it; the
  commit `main` gets is the one CI ran on. If CI fails, fix on the branch and push again; nothing on `main` changes. If
  `main` moved meanwhile, rebase the branch onto it, set the changelog date to that day, push it with
  `--force-with-lease`, and wait for CI again. After the release, delete the branch, local and remote. Alternatives: a
  pull request (rejected by the maintainer: one more step per release for a one-person project), or fast-forwarding
  `main` first and tagging once its run is green (rejected: a red run leaves `main` and the badge naming a version that
  has no tag).
- **commitlint lints from the merge-base when `before` is no commit.** The first push of a branch has an all-zero
  `github.event.before`, and a forced push one the clone lacks; `commitlint --from` then fails on no bad message. When
  `git cat-file -e "$FROM^{commit}"` fails, `FROM` becomes `git merge-base origin/main "$TO"`, the commits the branch
  adds. A rewritten `main` gets the same fallback, which lints nothing rather than failing.
- **Tag after the push, annotated, `v`-prefixed.** Tag the release commit with
  `git tag -a v<version> -m "skill-graft <version>"`, then push the tag alone. CI does not run on tags, so this order is
  what makes the tagged commit a checked one. `v` matches the sibling repositories and uv's and pip's
  `git+…@v<version>`. Annotated, so the tag records who tagged and when. Alternative: a lightweight tag. Rejected: it
  carries no date or tagger, and `git describe` skips it by default.
- **GitHub release notes are the changelog section, verbatim.** Publish with
  `gh release create v<version> --verify-tag --title "skill-graft <version>" --notes-file <file>`, the file holding the
  lines after that version's heading up to the next `## [` heading or the first link definition (`[x]: …`), whichever
  comes first, trailing blank lines dropped: the oldest version has no heading after it, only the link definitions.
  `--verify-tag` refuses to create a tag the release would otherwise make on the remote's default branch. Alternative:
  `--generate-notes`. Rejected: it lists pull requests and commits, not what a user sees.
- **README names the pattern, not a version.** Installation gains one sentence: append `@v<version>` to the git URL to
  install a release, listed under the repository's releases. A pinned `@v0.1.0` in every install line would go stale
  with the next release unless every release also edited the README.
- **`0.1.0` is cut in this change**, as its last task, by the steps it documents, so the documented steps are the ones
  that worked. `pyproject.toml` already says `0.1.0`; the release commit changes only `CHANGELOG.md`.

## Risks / Trade-offs

- [mdformat or markdownlint rewrites or rejects the link definitions] → run pre-commit on the release commit before
  tagging; markdownlint's MD053 accepts them since the headings use them as shortcut references.
- [A wrong tag is pushed] → before anyone installs it, `gh release delete v<version> --cleanup-tag --yes` removes
  release and tag; once someone may have installed it, leave it and release a fixed patch version instead.
- [A commit after the release commit is what CI checked] → tag only the commit the release branch's run checked; for
  `0.1.0`, later commits on this change's branch only archive it (`openspec/` moves) and come after the tag.

## Migration Plan

For `0.1.0` the release commit is a task of this change, so it sits on `feat/opsx-release-process` in place of
`release/v0.1.0`; it is pushed as `release/v0.1.0`, the CI change riding in the same push, since a push runs the
workflow of the commit pushed. Tagging is a task, so the archive commit comes after the tag: apply the CI, documentation
and release-commit tasks, push the branch as `release/v0.1.0`, wait for CI, fast-forward and push `main`, tag and
publish `0.1.0`; then tick that task and archive on the branch, and fast-forward and push `main` again. Each push is
confirmed with the user first.

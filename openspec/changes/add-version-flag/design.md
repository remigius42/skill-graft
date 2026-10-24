# Design

## Context

`cli.py` builds an argparse parser on every run; the version is `pyproject.toml`'s `version`, readable once installed
through `importlib.metadata`. Installers that follow PEP 610 (pip, uv, pipx) write `direct_url.json` into the installed
distribution's metadata, saying where it came from.

## Goals / Non-Goals

**Goals:**

- Name the installed code exactly enough for a bug report, with the standard library only.

**Non-Goals:**

- APM's version: the bug template asks for `apm --version` itself.
- A commit for an editable or folder install: the working tree may differ from any commit anyway.

## Decisions

- **`direct_url.json`, not `git`.** A git install keeps no repository to ask; the installer's record is the only
  source, and it needs no subprocess. Read with `importlib.metadata.distribution("skill-graft").read_text(...)`.
  Alternative: write the commit into the package at build time (a version plugin for the build backend), rejected as
  a new build dependency for one line.
- **Format `(<requested_revision> @ <commit_id[:7]>)`.** `requested_revision` is the ref the user typed (`main`,
  `v0.2.0`), the commit what it pointed at then. PEP 610 makes `requested_revision` optional; without it, when it is
  not a non-empty string, or when `commit_id` starts with it (an install pinned to a full or short hash),
  `(<commit>)`. Only `vcs_info.vcs == "git"` gets a suffix, as the spec speaks of git only. The README's install
  commands name no ref, so `(<commit>)` is what most users see.
- **Anything unexpected prints the version only.** No `direct_url.json`, one that is not JSON, not an object, without
  a `vcs_info` object, or without a string `commit_id`: none is an error, as `--version` must not fail.
- **A custom `argparse.Action`, not `action="version"`.** The built-in one passes its string through the help
  formatter, which `_Formatter` rewraps at the terminal's width, and takes it when the parser is built, so every
  command would read the metadata. The custom action computes the line only when `--version` is given, writes it to
  standard output as is, and exits 0, before the command check.
- **No fallback for a missing installation.** The `skill-graft` command exists only once installed, and each
  installation's entry point finds its own metadata, so each reports its own version.

## Risks / Trade-offs

- [An installer that skips PEP 610] → the version only, as for a release; no worse than today.
- \[`requested_revision` is a moving branch\] → the commit beside it pins it.

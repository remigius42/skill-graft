# Design

## Context

`cli.py` builds an argparse parser; the version is `pyproject.toml`'s `version`, readable once installed through
`importlib.metadata`. Installers that follow PEP 610 (pip, uv, pipx) write `direct_url.json` into the installed
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
  Alternative: write the commit into the package at build time (a version plugin for the build backend), rejected as a new
  build dependency for one line.
- **Format `(<requested_revision> @ <commit_id[:7]>)`.** `requested_revision` is the ref the user typed (`main`,
  `v0.2.0`), the commit what it pointed at then. PEP 610 makes `requested_revision` optional; without it, `(<commit>)`.
- **Anything unexpected prints the version only.** A missing or malformed `direct_url.json`, or one without
  `vcs_info`, is not an error: `--version` must not fail.
- **argparse's `action="version"`** with the string computed when the parser is built. It exits 0 before the command
  check, so `--version` needs no command; computing it on every run is one small file read.

## Risks / Trade-offs

- [An installer that skips PEP 610] → the version only, as for a release; no worse than today.
- \[`requested_revision` is a moving branch\] → the commit beside it pins it.

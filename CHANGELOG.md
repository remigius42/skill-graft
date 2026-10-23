# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- On Claude Code, `/graft-check` reads **Skill** text only through headless readers, `claude -p --restricted` limited
  to `Read`, `Grep` and `Glob`, without MCP servers and confined to that **Skill**'s folders; its own session sees
  only CLI output and the readers' reports. A **Patch** it proposes is written by a patcher confined to a temporary
  folder, and you read its diff before it enters the **Package**. Elsewhere, or with a `claude` lacking those flags,
  it says the **Check** is unhardened and why, and reads only on your yes
- A warning for invisible characters common as copy-paste debris (zero-width, soft hyphen, bidi marks), once per file
  with its first line and count
- `docs/security.md` and a Security section in the README: what APM and skill-graft block, what the **Check**
  enforces on Claude Code, running it in Claude Code's sandbox, and the residual risks

### Changed

- **BREAKING**: resolution fails when a **Hull** **Skill** holds a **Hidden character**, in its **Upstream** text, a
  file or folder name, or the lines its **Patches** add, naming each file, line and character class; one run reports
  them all. `resolve`, `build` (`--into` too), `update` and the editing commands write nothing; `why` and `tree` print
  the **Hull**, then fail. Such a **Hull**'s `build` already failed in APM; now `resolve` fails too
- **BREAKING**: a Markdown file of a **Hull** **Skill** that is not UTF-8, **Upstream** or as patched, fails resolution
  instead of being skipped with a warning; so does any file of it that cannot be read

### Security

- A `SKILL.md` that a git **Source** links outside its **Skill**, or that is not a regular file (a FIFO or device, or a
  link to one), is no longer read, so a **Source** can neither make skill-graft read a local file nor hang it. Such a
  **Skill**'s name is unreadable: an **Entry** or **Reference** naming its folder fails, naming the `SKILL.md`, never
  what it links to; other **Entries** never see it

## [0.1.0] - 2026-10-22

### Added

- `skill-graft init` creates the package, `~/.apm/skill-graft/`, with a commented `skill-graft.toml`, and
  registers it with APM. `init --project` creates one in the project instead, `.apm/skill-graft/`, registered in
  the project's `apm.yml`; every command then acts on the nearest package above the working folder, and on the
  user scope's when there is none
- `skill-graft build` vendors the hull into the package's `.apm/skills/` and deploys it through APM into Claude
  Code, opencode and the other harnesses APM supports; `--no-install` stops before APM, and `--into <dir>` writes
  the skills and the lock into an empty folder instead, leaving the package and APM untouched
- Sources: local folders (`path`) and git repositories (`git`, with an optional `branch`), each git source read at
  the commit its `ref` names and cached outside the package. `subdirectory` reads only one folder of a
  repository, as if it were its root
- `skill-graft update [source…] [--dry-run]` moves each git source's `ref` to its branch tip, only if the hull
  still resolves and every patch still applies there, and prints which skills that adds, removes or changes
- The hull: the entries plus every skill they reach through slash references (`/grilling`) and Skill tool
  references (`Skill(grilling)`, or a sentence telling the reader to call the Skill tool with `grilling`), found
  in every Markdown file of a skill. A reference resolves in its own source first, else in exactly one other;
  one matching no skill is a warning. Prose references to a skill outside the hull become suggestions to `add`
- `skill-graft resolve` computes the hull, writes `skill-graft.lock` and prints the hull as a tree, followed by
  the suggestions
- `[bind]`, and `skill-graft bind` and `unbind`: fix which skill a name from one source resolves to, or make it no
  reference at all with `false`
- `[rename]` and a source's `prefix` set a skill's deployed name, carried into its folder, its `name:` and every
  reference to it, prose included; `skill-graft rename` sets or undoes a rename. Deployed names must be unique
  across the hull; a name a harness already uses, such as `code-review`, is a warning, and one in your own
  `reserved` list an error
- `[patches]`: unified diffs applied to a skill's upstream text before its references are read, so a patch can
  change what a skill calls. A patch that fails names each failing hunk, and nothing is written
- `skill-graft tree [--format text|mermaid] [--link]` and `skill-graft why <skill>` explain the hull without
  writing anything: the whole tree, as text, Mermaid or a mermaid.live link, or the paths from the entries to one
  skill and its upstream folder
- `skill-graft add` and `remove` change `entries`, keeping the file's comments, once the result resolves
- `skill-graft help [command]`, and `--help` on every command
- The `graft-check` skill, in this repository's `skills/`: run as `/graft-check`, it has an agent read a built
  package for missed, false or misdirected references, wrong rewrites and links vendoring broke, and proposes
  `add`, `bind`, `unbind` or a patch for each, applied only once you accept

[0.1.0]: https://github.com/remigius42/skill-graft/releases/tag/v0.1.0
[unreleased]: https://github.com/remigius42/skill-graft/compare/v0.1.0...HEAD

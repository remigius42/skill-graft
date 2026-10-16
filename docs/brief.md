# Brief

The decisions made before this repository existed, as input for a `grill-with-docs` session. Once the grill has
turned them into `CONTEXT.md` and ADRs, delete this file.

## Problem

Skill packs reference each other by name: `/tdd`, "call the Skill tool with `grilling`", or plain prose such as
"use code-review". Installing one skill from a pack silently drops the skills it calls. Renaming a skill to dodge
a harness built-in (Matt Pocock's `code-review` against Claude Code's `/code-review`, mattpocock/skills#483) has
to rewrite every one of those references, and upstream updates undo a rename made by hand.

Namespacing does not solve it portably. Claude Code plugins expose `plugin:skill`, but Pi and opencode keep one
flat namespace keyed by the `name:` front matter: Pi forbids `:` in names and keeps the first duplicate, opencode
keeps the last. A distinctive name (`mp-code-review`) is the one reference every harness resolves the same way.

## Decisions

### Files

All under `~/.apm/skill-graft/`:

| File                  | Written by    | Holds                                                     |
| --------------------- | ------------- | --------------------------------------------------------- |
| `skill-graft.toml`    | the user      | intent: sources, entries, renames, binds, patches         |
| `skill-graft.lock`    | `resolve`     | provenance: resolved shas, the hull and its edges, hashes |
| `patches/`            | the user      | unified diffs for content changes                         |
| `apm.yml`             | `build`, once | `name` and `version`, nothing else                        |
| `.apm/skills/<name>/` | `build`       | the vendored, patched skills and the files they reference |

`resolve` never rewrites `skill-graft.toml`; commands that edit it on purpose (`add`, `rename`) use `tomlkit` so
comments and formatting survive. The user's `~/.apm/apm.yml` holds one dependency, `path: ~/.apm/skill-graft`.

### Config

```toml
entries = ["mp/tdd", "mp/implement", "own/chisel"]

[sources.mp]
git = "https://github.com/mattpocock/skills.git"
ref = "<sha>"

[sources.own]
path = "~/Documents/sync/2_areas/software/chisel_skill"

[rename]
"mp/code-review" = "mp-code-review"

[bind]
"mp/grilling" = "mp/grilling"

[patches]
"mp/implement" = ["patches/implement-no-pr.patch"]
```

### Resolution

- A skill is `source/name`. A bare reference in a skill's body resolves within its own source first, then the
  other sources in declared order. A reference more than one source satisfies is an error until `bind` settles
  it. Only `bind` points a reference across sources.
- References are followed in three forms: `/name`, the Skill tool form, and bare prose. Bare prose is followed
  only when the name cannot be an ordinary word: hyphenated, or in backticks. `pr`, `research`, and `implement`
  stay unfollowed in plain prose.
- Files a skill references outside its own folder (`docs/agents/issue-tracker.md`) are vendored with it.
- Every deployed name is unique across sources and against a maintained list of harness built-ins. A clash stops
  the build until `rename` resolves it.

### Patching

- Patching happens before APM, never after: APM reports a hand-edited deployed file as `modified` drift.
- A rename is a declared operation applied across the graph: the folder, `name:` (APM requires it to equal the
  folder), and every matched reference. A diff would break on every upstream bump.
- Content changes are unified diffs. A hunk that no longer applies fails the update loudly.

### Feedback

The lock records each edge with its kind (`/slash`, Skill tool, prose, bind), so the explanation is a view of it:

- `resolve` ends with a tree in the style of `cargo tree`: one line per pulled-in skill naming what pulled it in,
  renames marked, unresolved prose listed.
- `skill-graft why <skill>` prints the reverse paths.
- `skill-graft tree --format mermaid` renders the same graph for documentation.

### Stack

- Python 3.11 or later: APM is Python (`apm-cli` on PyPI), so no second runtime. `tomllib` reads, `tomlkit`
  writes. `git` and `apm` run as subprocesses.
- Packaged with `uv`, installed with `uv tool install`. The CLI is `skill-graft`, not a shorter name that could
  clash on `PATH`; it runs rarely, so the length costs little.

## Measured APM behavior

APM 0.33.0, `apm install -g -t claude`, with `HOME` pointed at a scratch directory:

- A local package without `apm.yml` is rejected, for both `skills/<name>/` and `.apm/skills/<name>/`:
  `not a valid APM package (no apm.yml, SKILL.md, or plugin.json)`. With a two-line `apm.yml`, every
  `.apm/skills/<name>/` deploys to `~/.claude/skills/`, sibling files included.
- `path: ./skill-graft` in `~/.apm/apm.yml` fails whatever the working directory, with exit code 1. Without
  `-v` the output still ends in "No changes -- install state already up to date". `~/.apm/skill-graft` and
  absolute paths work.
- Removing a skill and reinstalling prunes it from `~/.claude/skills/` ("3 stale files cleaned").

## Open

- The list of harness built-ins: where it comes from and how it stays current.
- What `build` does with a skill whose references cannot be resolved at all.
- Whether `update` bumps one source's `ref` and re-resolves, or only re-resolves.

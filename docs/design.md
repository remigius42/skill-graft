# Design

How skill-graft works, as decided before the first OpenSpec change. Terms are defined in `CONTEXT.md`, the
reasons for the less obvious choices in `docs/adr/`. OpenSpec specs replace this file as they land.

## Files

All under `~/.apm/skill-graft/`:

| File                  | Written by                          | Holds                                                       |
| --------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `skill-graft.toml`    | the user; `add`, `rename`, `update` | intent: sources, entries, renames, binds, patches, reserved |
| `skill-graft.lock`    | `resolve`, `build`, `update`        | provenance: resolved shas, the hull and its edges, hashes   |
| `patches/`            | the user                            | unified diffs for content changes                           |
| `apm.yml`             | `init`                              | `name` and `version`, nothing else                          |
| `.apm/skills/<name>/` | `build`                             | the vendored, patched, renamed skills                       |

`resolve` never rewrites `skill-graft.toml`. Commands that edit it on purpose use `tomlkit`, so comments and
formatting survive. The lock is output only: never an input that overrides the TOML.

Git sources are cached outside the package, under `$XDG_CACHE_HOME/skill-graft/` (else `~/.cache/skill-graft/`):
one bare repository per URL and one export per commit, the committed bytes exactly. Deleting it loses nothing.

## Config

```toml
entries = ["mp/tdd", "mp/implement", "own/chisel"]
reserved = ["review"]

[sources.mp]
git = "https://github.com/mattpocock/skills.git"
branch = "main"  # optional; defaults to the remote's default branch
ref = "<sha>"

[sources.own]
path = "~/Documents/sync/2_areas/software/chisel_skill"

[rename]
"mp/code-review" = "mp-code-review"

[bind]
"mp/grilling" = "own/grilling"
"mp/tmp" = false  # `/tmp` from `mp` is not a reference

[patches]
"mp/implement" = ["patches/implement-no-pr.patch"]
```

## Commands

- `init`: creates `~/.apm/skill-graft/` with a commented `skill-graft.toml` and the two-line `apm.yml`, then
  registers it with `apm install -g <absolute path of ~/.apm/skill-graft>`. Refuses if the folder exists.
- `add <skill-id>`, `rename <skill-id> <name>`: edit the TOML, then resolve.
- `resolve`: computes the hull from the TOML, writes the lock, prints the tree, warnings and suggestions.
  Reads every declared source, each git one at its `ref`, fetching only when that commit is not cached.
- `build`: resolves, writes `.apm/skills/`, then the lock, then runs the same `apm install -g` as `init`.
  `--no-install` stops before APM. Fails unless `apm` exits 0 and `~/.apm/apm.yml` lists `~/.apm/skill-graft`.
- `update [source…]`: fetches, resolves at each branch tip, and only if that succeeds writes the lock, and the
  tips' shas into `ref` when one moved; prints the hull diff (`+` added, `-` removed, `~` changed, against the
  hull at the current refs if those are cached, never fetching for it) and any failing patch hunks. `--dry-run`
  does all of it without writing the TOML, the lock or the cache.
- `why <skill>`: the reverse paths from the entries.
- `tree [--format mermaid]`: the hull as a tree, or as Mermaid for documentation.

## Resolution

- A skill is its whole folder. Everything in it is vendored; nothing outside it is.
- References are found in every Markdown file of a skill, code blocks included, in three forms: `/name` as
  its own token (never part of a path, URL, link target or attribute), the Skill tool's call form
  `Skill(name)` (quoted or not, as `skill=` or `skill:`, further arguments allowed), and prose. Prose counts
  only when the name cannot be an ordinary word: a code span holding just a name, or a bare lowercase hyphenated
  token bounded as a slash name is (never in a path, URL, query, link target, attribute or `#` anchor, nor a
  YAML key such as `allowed-tools:`). A Skill tool call's further arguments belong to it, never prose. The
  `name:` line of a skill's own `SKILL.md` is never a reference. Names match case-sensitively.
- Slash and Skill tool references extend the hull. They resolve in their own source first, else in exactly
  one other source; several other sources is an error until a bind settles it. One that matches no skill in
  any declared source is a warning: "`mp/tdd` calls `/foo`: no declared source has a skill `foo`", naming the
  `"mp/foo" = false` bind that silences it. A bind no reference uses is a warning too.
- Prose references resolve only in their own source, to the one skill of that name there, and never extend
  the hull. One inside the hull is an edge of kind `prose` and is rewritten on rename; one outside it is
  suggested (add it to `entries` to accept, until `add` exists); one that matches nothing, or several skills, is
  not a reference and says nothing.
- A bind overrides all of this, for every form. A bind to `false` makes the name no reference at all. A
  reference bound to a skill of another name is rewritten to that skill's deployed name.

## Names

A skill's deployed name is its `[rename]` value, else its name. `build` vendors it to
`.apm/skills/<deployed name>/`, sets a renamed skill's `name:` (quoted when YAML would misread it plain), and
rewrites every reference, in every UTF-8 Markdown file of every hull skill, whose target's deployed name differs
from the name written. A rename that names no hull skill is a warning.

Deployed names must be unique across the hull and avoid reserved names, both compared ignoring case. The shipped
list is the built-in commands, bundled skills and aliases of Claude Code and Codex, taken from their docs:

| Clash                                       | Severity                           |
| ------------------------------------------- | ---------------------------------- |
| the reserved list skill-graft ships         | warning, with a suggested `rename` |
| the user's `reserved`                       | error                              |
| two hull skills with the same deployed name | error                              |

## Order

Patches apply first, to the upstream text; then references resolve; then renames rewrite the folder, `name:`
(APM requires it to equal the folder), and every reference. Patches never mention a deployed name, and a hunk
that no longer applies fails loudly. Patching happens before APM, never after: APM reports a hand-edited
deployed file as `modified` drift.

## Feedback

The lock (TOML, sorted, never read back) records each source's `ref` or folder, each hull skill with a SHA-256
of its folder as vendored (rewrites applied) and its `deployed` name when renamed, each edge with its kind
(`slash`, `skill-tool`, `prose`) plus `bind = true` when a bind decided it, and each prose suggestion with the
skills mentioning it, so the explanation is a view of it:

- `resolve` prints a tree in the style of `cargo tree`: one line per edge naming the reference as written
  upstream, each skill expanded once and later lines marked `(*)`, a renamed skill as `<id> as <deployed name>`,
  and a prose edge only when the build rewrites it; then the prose suggestions, and the warnings on stderr.
- `why` and `tree` read the lock.

## Stack

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
- `apm install -g <absolute path>` creates `~/.apm/apm.yml` if missing and lists the package under
  `dependencies.apm` as an absolute path, never with `~`. Repeating it changes nothing ("updated ref in
  apm.yml") and redeploys. A package of just the two-line `apm.yml`, with no skills yet, registers too.
- Without `-t` and without `targets:` in `~/.apm/apm.yml`, skills deploy to `~/.agents/skills/`.

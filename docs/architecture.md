# Architecture

How skill-graft is built, and why, where the specs in `openspec/specs/` state only what it does. Terms are defined in
[CONTEXT.md](../CONTEXT.md), the reasons for the less obvious choices in [adr/](adr/). This file replaced
`docs/design.md`, which is in git: as first written before any OpenSpec change, `git show f10e879:docs/design.md`; as
last kept, before its deletion, `git show "$(git rev-list -n 1 HEAD -- docs/design.md)^:docs/design.md"`.

## Files

All in the package: `~/.apm/skill-graft/` (user scope), or `<project>/.apm/skill-graft/` (project scope, made by
`init --project`). Every command but `init` uses the nearest `.apm/skill-graft/` in or above the working folder, below
the home folder, or up to the root outside it; else the user scope's
([ADR 0004](adr/0004-user-scope-is-the-default.md)).

| File                  | Written by                                              | Holds                                                       |
| --------------------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| `skill-graft.toml`    | the user; `update` and the editing commands             | intent: sources, entries, renames, binds, patches, reserved |
| `skill-graft.lock`    | `resolve`, `deploy`, `update`, and the editing commands | provenance: resolved shas, the hull and its edges, hashes   |
| `patches/`            | the user                                                | unified diffs for content changes                           |
| `apm.yml`             | `init`                                                  | `name` and `version`, nothing else                          |
| `.apm/skills/<name>/` | `resolve`, `deploy`, `update`, and the editing commands | the vendored, patched, renamed skills                       |
| `.gitattributes`      | `resolve`, `deploy`, `update`, and the editing commands | `-text` for `.apm/skills/` and `patches/`, if missing       |

`deploy --into <dir>` writes the lock and `.apm/skills/` into `<dir>` instead, leaving the package as it is, and writes
no `.gitattributes`. `resolve` never rewrites `skill-graft.toml`. Commands that edit it on purpose use `tomlkit`, so
comments and formatting survive. `.gitattributes` keeps git from converting the committed copies' and patches' line
endings, which would read as edits.

## Writing the copies and the lock together

Every command that vendors writes `.apm/skills/` and the lock through `commands/transaction.py`: it stages the copies in
`.apm/skills.new/` while the patched folders exist, then, after the TOML, swaps them in (the previous ones to
`.apm/skills.old/`) and writes the lock; on any failure the swap is undone and the TOML restored. A run killed mid-swap
is recovered by the next writing one: `skills.old` is kept when it holds exactly the lock's copies, else `skills`.

## Cache

Where the cache lives and what prunes it is in the [README](../README.md#cache). Each repository is a bare one, cloned
blobless: commits and trees, and the files of each export, fetched in one request when the export is first made. So the
first export of a commit and `subdirectory` needs the remote even when the commit is cached; an export pruned and made
again does not. Each export holds the committed bytes exactly. Each commit read is pinned as a ref
`refs/skill-graft/<sha>` in its repository, so `fetch --prune` and git's gc keep it after it vanishes upstream.

## Applying patches

`git apply` runs in an owner-writable temporary copy of the skill's folder, never in the cache, one copy per resolution
(`update` makes two, open at once: at the current refs and at the tips). Its environment has every `GIT_CONFIG*`
variable removed, `HOME` and `XDG_CONFIG_HOME` pointed at an empty folder, `GIT_CONFIG_NOSYSTEM=1`,
`GIT_ATTR_NOSYSTEM=1` (no system gitattributes converting line endings) and `GIT_CEILING_DIRECTORIES` at the copy's
parent, so no user, system or environment setting, and no enclosing repository, changes what applies or what it writes,
on any git version.

Patches apply before references resolve, and renames after both: a patch never mentions a deployed name, and the rename
sets `name:`, which APM requires to equal the folder. Patching happens before APM, never after: APM reports a
hand-edited deployed file as `modified` drift.

## Hidden character scan

The classes are APM 0.35.0's (`apm_cli/security/content_scanner.py`), copied as ranges since `apm_cli` is no API. The
upstream folder is scanned, not only the patched copy, because the **Check** reads it; of a patch only the `+` lines,
since the lines it keeps repeat upstream ones. A non-Markdown file without a UTF-32 or UTF-16 byte order mark is read
strictly as UTF-8 with NUL bytes included, so a NUL cannot switch the scan off, and skipped as binary only when it fails
that and holds a NUL: scanning random bytes leniently turns up a bidi control about once per 2 MB. Lone surrogates are
in no class: strict decoding refuses them, lenient decoding replaces them.

## Links in the Mermaid tree

`tree --format mermaid` links only git sources on `github.com` and `gitlab.com`: a URL can hold a token in its user
info, query or path, and only there is the path `owner/repo`, names a token would not fetch. The repository URL is
rebuilt from the host and the name segments, never stripped of credentials, so nothing else from the configured URL
appears. A URL git rewrites (`insteadOf`) gets no link, since git may fetch it from a host taking a token in the path.
Links are `<a>` tags rather than `click` lines, which mermaid.live opens in the same tab. A label writes `"` as
`#quot;`, though none can hold one today: names, aliases and prefixes cannot, and a Skill tool reference is shown
normalized, as `Skill(name)`.

## The lock's version

The lock holds `version = 1`. Any change to its keys or to what they mean raises `version`, since the `graft-check`
skill reads version 1 only. `test_version_1_keys` in `tests/pipeline/test_lock.py` fails on a change to the keys, as a
reminder; a change to what a key means, no test catches.

## Source layers

`src/skill_graft/` is layered, each layer importing only those below it, as `lint-imports` enforces:

- `cli.py`, the console entry point: it parses and dispatches, reaching `pipeline/` and `infra/` only through
  `commands/`, `infra.errors` aside.
- `commands/`: the commands, `resolve`, `deploy`, `update`, `init_package` (`init`), `edit` (`add`, `remove`, `rename`,
  `bind`, `unbind`), `explain` (`why`, `tree`) and `vet`; `scope`, which builds the `Scope`; `transaction`, which writes
  the copies and the lock together; `review`, the hull diff and the Deployed diff those that write the lock share (built
  by `pipeline/deployed.py`); and `housekeeping`, which prunes the cache after a command. Each command builds the one
  git `Cache` it reads through.
- `pipeline/`: config to **Hull** to vendored skills and lock, `compute.compute_hull` computing the **Hull**; `vet`
  holding the patterns and `vet.scan`, which flags one **Skill** as deployed.
- `infra/`: `files` (walking, checking and copying a skill, atomic writes), `git`, `apm`, `cache` (the git sources'
  cache), `paths` (where skill-graft and APM keep their files), `text` (the hidden character table and escaping output),
  and `errors`.

`pipeline/` and `infra/` take the `Scope` and the `Cache` as parameters; nothing holds either globally
([ADR 0008](adr/0008-scope-is-passed-not-global.md)). The CLI is `skill-graft`, not a shorter name that could clash on
`PATH`; it runs rarely, so the length costs little. APM is Python, so skill-graft is too: no second runtime.

# Design

How skill-graft works, as decided before the first OpenSpec change. Terms are defined in `CONTEXT.md`, the
reasons for the less obvious choices in `docs/adr/`. OpenSpec specs replace this file as they land.

## Files

All in the package: `~/.apm/skill-graft/` (user scope), or `<project>/.apm/skill-graft/` (project scope, made by
`init --project`). Every command but `init` uses the nearest `.apm/skill-graft/` above the working folder, up
to the home folder, else the user scope's (ADR 0004).

| File                  | Written by                                             | Holds                                                       |
| --------------------- | ------------------------------------------------------ | ----------------------------------------------------------- |
| `skill-graft.toml`    | the user; `update` and the editing commands            | intent: sources, entries, renames, binds, patches, reserved |
| `skill-graft.lock`    | `resolve`, `build`, `update`, and the editing commands | provenance: resolved shas, the hull and its edges, hashes   |
| `patches/`            | the user                                               | unified diffs for content changes                           |
| `apm.yml`             | `init`                                                 | `name` and `version`, nothing else                          |
| `.apm/skills/<name>/` | `build`                                                | the vendored, patched, renamed skills                       |

`build --into <dir>` writes the lock and `.apm/skills/` into `<dir>` instead, leaving the package as it is.

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
prefix = "mp-"  # optional; every skill of `mp` deploys as mp-<name>

[sources.cp]
git = "https://github.com/cursor/plugins.git"
ref = "<sha>"
subdirectory = "pstack/skills"  # optional; read only this folder of the repository

[sources.own]
path = "~/Documents/sync/2_areas/software/chisel_skill"

[rename]
"own/chisel" = "own-chisel"
"mp/tdd" = "tdd"  # wins over the prefix

[bind]
"mp/grilling" = "own/grilling"
"mp/tmp" = false  # `/tmp` from `mp` is not a reference

[patches]
"mp/implement" = ["patches/implement-no-pr.patch"]
```

## Commands

- `init`: creates `~/.apm/skill-graft/` with a commented `skill-graft.toml`, including the lines that install
  graft-check, and the two-line `apm.yml`, then
  registers it with `apm install -g <absolute path of ~/.apm/skill-graft>`. Refuses if the folder exists.
  `init --project` does the same in `./.apm/skill-graft/`, registering it with `apm install ./.apm/skill-graft`
  run there; refused in the home folder, and if APM leaves it unregistered, the folder is removed again.
- `add <skill-id>…`, `remove <skill-id>…`, `rename <skill-id> <name>`, `bind <alias>/<name> <target>`,
  `unbind <alias>/<name>`: resolve the edited config in memory and only if that succeeds write the TOML (in place,
  as `update` does), then the lock, and print what `resolve` prints. Notices go to stderr with the warnings. Never
  build. An edit that changes nothing (every skill ID already an entry, the current deployed name, the current
  bind) prints only its notices and neither resolves nor writes.
- `add` appends each skill ID to `entries` (creating the key before the first table if absent). An unknown alias
  or skill is an error; one already an entry is a notice and left alone; one already in the hull is added with a
  notice naming the skill that reaches it from the other entries.
- `remove` deletes each skill ID from `entries`, the last one too. One that is no entry is an error; one still in
  the hull is removed with a notice naming the skill that reaches it from the remaining entries. Both notices come
  from one breadth-first walk of the edited hull's slash and Skill tool edges, so the parent named is never
  reached only through the skill itself. No command edits patches or `reserved`, and only
  `update` edits sources (their `ref`).
- `rename` sets the skill's `[rename]` value (appending the table if absent); renaming to the name it deploys as
  without a key (its source's `prefix`, if any, before its upstream name) removes the key, which is how a rename
  is undone, so under a prefix the upstream name is written as a key; the current deployed name is a notice. An
  unknown alias or skill is an error; a skill outside the hull gets the unused-rename warning; clashes are the
  usual errors and warnings, an error writing nothing.
- `bind` sets `[bind]` key `<alias>/<name>` to a skill ID, or to `false` for the word `false` (appending the
  table if absent). The key's alias must be declared, its name need not be a skill; resolving checks the target, as
  it checks every bind's. A key already set has its target checked first, as `rename` checks its skill, so the
  current value is a notice only while its target exists. An unused bind gets the usual warning.
- `unbind` deletes the key, leaving the table; its key is parsed as `bind`'s, and one not in `[bind]` is an error.
- `resolve`: computes the hull from the TOML, writes the lock, prints the tree, warnings and suggestions.
  Reads every declared source, each git one at its `ref`, fetching only when that commit is not cached. A git
  source with `subdirectory` is read only in that folder of the commit, as if it were the root, confined to it as
  discovery confines a tree; it must be a folder of exactly that name there, with no symlink on the way, else the
  command fails naming the alias, the subdirectory and the commit. `subdirectory` is relative, without `.`, `..`,
  empty parts, `.git`, control characters or `.apm/skill-graft`; a path source points `path` at the folder instead.
- `build`: resolves, writes `.apm/skills/`, then the lock, then runs the same `apm install` as `init`, in the
  project root for a project package. `--no-install` stops before APM. Fails unless `apm` exits 0 and the
  scope's `apm.yml` (`~/.apm/apm.yml`, or the project's) lists the package. `--into <dir>` (not with
  `--no-install`) writes `<dir>/.apm/skills/` and `<dir>/skill-graft.lock` instead, the same lock bytes an
  in-place build writes, and never runs APM or changes the package. `<dir>` must be an existing, empty folder,
  not in a package (any `.apm/skill-graft` path, ignoring case), a path source's folder, or in or around the
  cache; a failed build removes what it wrote there. It prints no hint to `resolve` for prose suggestions,
  which would rewrite the package's lock; `<dir>`'s lock lists them.
- Writing commands (`init`, `resolve`, `build`, `update`, `add`, `remove`, `rename`, `bind`, `unbind`) first
  print `skill-graft: package: <path>`.
- `update [source…]`: fetches, resolves at each branch tip, and only if that succeeds writes the lock, and the
  tips' shas into `ref` when one moved; prints the hull diff (`+` added, `-` removed, `~` changed, against the
  hull at the current refs if those are cached, never fetching for it) and any failing patch hunks. `--dry-run`
  does all of it without writing the TOML, the lock or the cache. A tip without a source's `subdirectory` fails
  resolution, so `ref` stays.
- `why <skill>`: the reverse paths from the entries, as an inverted tree (`cargo tree -i`): the skill at the
  root, each child a skill whose slash or Skill tool reference reaches it, joined by `├─←` and `└─←`, labels and
  `(*)` as in `resolve`'s tree, an entry below the root marked `(entry)` and not expanded (the root always
  expands, marked `(entry)` if it is one); children in hull order; prose and self-references omitted.
  `<skill>` is a skill ID if it holds a `/`, else a deployed name. A bare name that is only the upstream name
  of a skill renamed or prefixed is an error naming its skill ID and deployed name. A skill outside the hull, by
  skill ID or by the bare name of a prose suggestion, is an error saying so, plus who mentions it in prose and
  the `add` hint.
- `tree [--format text|mermaid] [--link]`: the hull as `resolve`'s tree (without the suggestions), or as a
  Mermaid `flowchart TD`: nodes `n0…` in hull order labelled as tree lines are (`as <deployed>`, `(patched)`),
  entries in `classDef entry`, one edge per source, target, kind and bind labelled with the reference as written
  (`, bind`), prose edges dotted and only where the build rewrites them, no code fence, no links to sources.
  Labels are quoted, with `"` as `#quot;` and every backtick as `#96;`: a quoted label opening with a backtick is
  a Mermaid Markdown string. `--link` (Mermaid only) prints a `https://mermaid.live/edit#pako:…` URL instead: the
  diagram lives in the fragment, so nothing is uploaded and skill-graft makes no network call. The fragment is
  mermaid-live-editor's `pako` form, the JSON state `{"code": <diagram>, "mermaid": "{\"theme\": \"default\"}"}`
  zlib-deflated at level 9 in url-safe base64 without padding; the editor merges it over its default state.
- `help [command]`: the same text as `-h`/`--help`, which every command takes. No command, or an unknown one,
  prints the error and the command list to stderr and exits 2.

## Resolution

- A skill is its whole folder. Everything in it is vendored; nothing outside it is.
- References are found in every Markdown file of a skill, code blocks included, in three forms: `/name` as its own token
  (never part of a path, URL, link target or attribute, nor a quoted first argument or list item such as
  `fetch('/orders')`, nor after an interpolation as in `${id}/orders`, nor right after a closing code span as in
  `` `package.json`/x ``), the Skill tool's call form `Skill(name)` (quoted or not, as `skill=` or `skill:`, further
  arguments allowed) or a sentence naming it (`Call the Skill tool with "grilling".`: each name in double quotes or
  backticks after `Skill tool`, up to the sentence's end, counts when it names a skill and is silently no reference
  otherwise), and prose. Prose counts only when the name cannot be an ordinary word: a code span holding just a name, or
  a bare lowercase hyphenated token bounded as a slash name is (never in a path, URL, query, link target, attribute or
  `#` anchor, nor a YAML key such as `allowed-tools:`). A Skill tool call's further arguments belong to it, never prose.
  The `name:` line of a skill's own `SKILL.md` is never a reference. Names match case-sensitively.
- Slash and Skill tool references extend the hull. They resolve in their own source first, else in exactly
  one other source; several other sources is an error until a bind settles it. One that matches no skill in
  any declared source is a warning: "`mp/tdd` calls `/foo`: no declared source has a skill `foo`", naming the
  `skill-graft bind mp/foo false` that silences it. A bind no reference uses is a warning too.
- Prose references resolve only in their own source, to the one skill of that name there, and never extend
  the hull. One inside the hull is an edge of kind `prose` and is rewritten on rename; one outside it is
  suggested (`add` it to accept); one that matches nothing, or several skills, is
  not a reference and says nothing.
- A bind overrides all of this, for every form. A bind to `false` makes the name no reference at all. A
  reference bound to a skill of another name is rewritten to that skill's deployed name. Every bind's target
  must exist, used or not, so a typo fails the next `resolve`.

## Names

A skill's deployed name is its `[rename]` value, else its source's `prefix` before its name, else its name. A
prefix covers every hull skill of its source, dependencies a later `update` pulls in included, and is used as
written (`prefix = "mp"` gives `mptdd`). `build` vendors a skill to `.apm/skills/<deployed name>/`, sets the
`name:` of one whose deployed name differs from its name (quoted when YAML would misread it plain), and rewrites
every reference, in every UTF-8 Markdown file of every hull skill, whose target's deployed name differs from the
name written. A rename that names no hull skill is a warning.

Deployed names must be unique across the hull and avoid reserved names, both compared ignoring case. A hint
suggests a `[rename]` line only for a skill with neither a key nor a prefix; for one with a key it names the value
to change, for a prefixed one the key to add or the `prefix` to change. The shipped list is the built-in
commands, bundled skills and aliases of Claude Code and Codex, taken from their docs:

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

## Patches

- `[patches]` maps a skill ID of a declared source to a non-empty list of patch files, each relative to the
  folder holding `skill-graft.toml` (`~` expanded); `patches/` is a convention. A file listed twice under one
  key, compared as resolved paths, is an error; one file under several keys is fine.
- `git apply -p1 --whitespace=nowarn` runs as a subprocess in an owner-writable copy of the skill's folder, never
  in the cache, with every `GIT_CONFIG*` variable removed from its environment, `HOME` and `XDG_CONFIG_HOME`
  pointed at an empty folder and `GIT_CONFIG_NOSYSTEM=1`, so no user, system or environment setting changes what
  applies or what it writes, on any git version. Paths are relative to the skill folder (`a/SKILL.md`), as
  `git diff --relative` inside it or `diff -ruN base/ edited/` from their parent writes them. No fuzz: a hunk whose
  context moved only by offset applies, except that one starting at the file's first line stays anchored there; any
  other fails.
- The upstream folder is checked before it is copied, as the walk checks any skill before reading it. The copy
  leaves out `.git`, as vendoring does. Each resolution (`update` makes two: at the current refs and at the tips)
  copies into its own temporary folder, removed whatever the outcome, and `git apply` runs with
  `GIT_CEILING_DIRECTORIES` at its parent so no enclosing repository changes how paths resolve. `vendor` copies
  from them; messages and the lock name the upstream folder or a path inside the skill, never the copy. Without
  `git` on `PATH`, applying a patch is an error saying `[patches]` needs it; a config without patches never needs
  `git` for them.
- A patch may change, add or delete any file in the skill's folder, nothing outside it. It must not delete
  `SKILL.md` or change its name, as read from `name:` else the folder (so adding or removing `name:` counts):
  the skill ID comes from it, and a new name is a rename. Either is an error pointing at `[rename]`.
- The patched copy is checked like an upstream folder, so a symlink a patch creates fails wherever an upstream
  one would. Mode changes apply, but only `git diff` writes them. Lines `git apply` would skip as noise, losing a
  change without a word, are errors naming the patch file, at load: `Binary files … differ` (a binary change
  `diff` cannot express) and `Only in …` (an added or deleted file, from `diff` without `-N`). So is a
  `GIT binary patch` block: binary hunks are unsupported.
- A skill's patches apply when the walk reaches it, before it is scanned. A key naming no hull skill is a
  warning, as for `[rename]`; a listed patch file that is missing or unreadable is an error, used or not. Files
  in `patches/` that no key lists are ignored.
- A skill's patches apply in list order, each to the result of the one before. Applied with `--reject`, a failing
  patch names every hunk that failed (patch file, target file, `@@` header), read from the `.rej` files rather than
  git's localized messages; only `.rej` files the patch created or rewrote count, not ones the upstream folder
  ships untouched. A patch git refuses whole (a file to change is gone, a file to create exists, the patch is
  malformed) leaves no new `.rej`: the error names the patch file and passes git's message on. A patched copy that
  changes the skill's name or fails the file checks is a failure of that patch too. The skill's later patches are
  reported as not tried. A skill whose patch failed is not scanned, so skills reached only through it are not
  reached; the walk goes on with the rest, so one run reports every patch failure among the skills it reaches.
  Another error stops the walk as before, reported after the patch failures collected so far. Any failure is an
  error in `resolve`, `build` and `update`, nothing is written, and the unused-key warnings (`[rename]`,
  `[patches]`, `[bind]`) are left out, since the hull is incomplete.
- No command writes patches; `README.md` gives the recipe. After a `resolve`, which re-exports a deleted cache,
  the user copies the skill's upstream folder, the last line of `why <skill>`, with `cp -rL` (links become files, as in
  skill-graft's own copy) to `base/` in a fresh `mktemp -d`, outside any repository, deletes `base/.git` if there
  is one, and in `base/`, with no `apply.*` git settings of its own, applies the skill's earlier patches with
  `git apply -p1`; then copies that to `edited/`, edits it and runs
  `LC_ALL=C diff -ruN base/ edited/ > patches/<name>.patch`, then adds the patch to the key's list.
- When `update` fails on a hunk, it names each failing skill's upstream folder at the tip (its export in the
  cache) to redo the patch against, after the skill's earlier patches, as above; `ref` stays, and the next
  `update` moves it once the patches apply. Until then `build` at the old `ref` fails too. `--dry-run` writes no
  cache, so it reports the hunks and says to run without `--dry-run` to fetch the tip.
- `update`'s hull diff applies today's patches at the current refs too (the lock is never read back), so `~`
  covers upstream and patch changes alike. When they fail there, it says only "no previous hull to compare
  (patches fail at the current refs)", without repeating the hunks.

## Feedback

The lock (TOML, sorted except `patches`, never read back, the same on every machine for a project package whose path
sources lie inside the project) records each source's `ref` and `subdirectory`, or folder (in project scope relative to
the package when inside the project), each hull skill with a SHA-256 of its folder as vendored (patches and rewrites
applied), its `upstream` folder (relative to its source's root: the cache export, `subdirectory` included, or the path
source's folder; `why` prints it absolute), its
`deployed` name when renamed or prefixed and its `patches` in apply order when patched, each edge with its kind
(`slash`, `skill-tool`, `prose`) plus `bind = true` when a bind decided it, and each prose suggestion with the skills mentioning
it, so the explanation is a view of it:

- `resolve` prints a tree in the style of `cargo tree`: one line per edge naming the reference as written
  upstream, each skill expanded once and later lines marked `(*)`, a renamed or prefixed skill as
  `<id> as <deployed name>`, a patched one followed by `(patched)`, and a prose edge only when the build rewrites
  it; then the prose suggestions, and the warnings on stderr.
- `why` and `tree` resolve as `resolve` does (fetching only an uncached commit, warnings on stderr, a failing
  patch an error) but write nothing, so they never see a missing or stale lock.

The lock holds `version = 1`. Any change to its keys or to what they mean raises `version`
(`tests/pipeline/test_lock.py` pins the keys), since the `graft-check` skill reads version 1 only.

That skill, `skills/graft-check/` in this repository, is the **Check** of ADR 0006, installed like any other skill from
a git source with `subdirectory = "skills"`. An agent builds `--into` a temporary folder, reads that lock, the output
of `why` and `tree`, and the vendored copies against their upstream folders, and proposes binds, entries and patches
for the user to accept. It takes no part in resolution.

## Stack

- Python 3.11 or later: APM is Python (`apm-cli` on PyPI), so no second runtime. `tomllib` reads, `tomlkit`
  writes. `git` and `apm` run as subprocesses.
- Packaged with `uv`, installed with `uv tool install`. The CLI is `skill-graft`, not a shorter name that could
  clash on `PATH`; it runs rarely, so the length costs little.
- `src/skill_graft/` is layered, each layer importing only those below it: `cli.py` (the console entry point);
  `commands/` (`edit`, `update`, `explain`, `init_package`); `pipeline/` (config to **Hull** to vendored skills
  and lock, `compute.compute_hull` computing the **Hull**); `infra/` (file system, `git`, `apm`, errors).

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

APM 0.33.0 at project scope, `apm install ./.apm/skill-graft` in a scratch repository, `HOME` a scratch directory:

- In the project root it creates `apm.yml` if missing and lists `./.apm/skill-graft` under `dependencies.apm`,
  relative; repeating it adds no second line. It also writes `apm.lock.yaml` and `apm_modules/`, adds
  `apm_modules/` to `.gitignore`, and creates `~/.apm` for its own state.
- It takes the working directory as the project root: run in a subfolder, it fails.
- Without a harness marker (`.claude/`, `.cursor/`, `.github/copilot-instructions.md`, …) and without `targets:`,
  it exits 2 with "No harness detected" and removes the `apm.yml` it had created.
- It deploys only to the detected harnesses; with every target, skills land in `.agents/skills`,
  `.claude/skills`, `.grok/skills` and `.kiro/skills` under the project root.
- Removing a skill from the package and reinstalling prunes it.

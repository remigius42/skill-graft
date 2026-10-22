# [skill-graft](https://github.com/remigius42/skill-graft)

[![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fremigius42%2Fskill-graft%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/remigius42/skill-graft/actions/workflows/ci.yml/badge.svg)](https://github.com/remigius42/skill-graft/actions/workflows/ci.yml)

Copyright 2026 [Andreas Remigius Schmidt](https://github.com/remigius42)

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the
whole graph, applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm)
to deploy into Claude Code, opencode, and the other harnesses APM supports.

Skills call each other (`/grilling`, "call the Skill tool with `domain-modeling`"), so taking one skill means
taking every skill it reaches. Installing a whole collection is fine for a large model, but on a smaller one the
full skill set crowds the context, and taking only a subset by hand means tracing those calls yourself, skill by
skill. skill-graft computes that hull, the skills you ask for plus every skill they call, and deploys only those
skills. Renames come with it: a skill named like a harness built-in (`code-review`) shadows it or is shadowed by it,
and renaming one skill by hand misses the other skills that call it by name.

Status: beta.

## Installation

skill-graft needs Python 3.11 or later. It is not on PyPI; install it from the repository with any of:

```sh
uv tool install git+https://github.com/remigius42/skill-graft
pipx install --python python3.11 git+https://github.com/remigius42/skill-graft
pip install git+https://github.com/remigius42/skill-graft      # into the active environment
pipenv install "skill-graft @ git+https://github.com/remigius42/skill-graft"
```

uv picks a suitable Python itself; pipx and pip use theirs, so point them at 3.11 or later. pipenv installs into
that project's environment: run it as `pipenv run skill-graft`.

skill-graft runs APM as a command, so `apm` must be on `PATH` as well, in version 0.33.0: the folders APM deploys
to were measured on it, and another version may deploy elsewhere. Install it the same way, e.g.
`uv tool install apm-cli==0.33.0`, `pipx install apm-cli==0.33.0` or `pip install apm-cli==0.33.0`.

## Usage

Besides skill-graft and APM, you need a harness folder for APM to deploy into, such as `~/.claude/` for Claude Code.
To deploy the `tdd` skill of [mattpocock/skills](https://github.com/mattpocock/skills), and every skill it calls,
create your package:

```sh
skill-graft init
```

`init` writes the package's config, `~/.apm/skill-graft/skill-graft.toml`, all commented out. Add the repository
to it as a source, a new table after the comments (the commented `[sources.mp]` there is only an example):

```toml
[sources.mp]
git = "https://github.com/mattpocock/skills.git"
```

Then:

```sh
skill-graft update mp    # set the source's ref to its branch tip
skill-graft add mp/tdd   # ask for the skill
skill-graft tree         # see the hull: mp/tdd and every skill it calls
skill-graft build        # vendor the hull and deploy it through APM
```

`tdd` and the skills it calls are now in `~/.claude/skills/`. To share skills through a project instead, see
[A package for one project](#a-package-for-one-project); to deploy them under other names, `[rename]` and `prefix`
in [Config](#config); to change what a skill says, [Writing a patch](#writing-a-patch).

## Commands

- `init [--project]`: create the package, `~/.apm/skill-graft/` (or `./.apm/skill-graft/`), and register it with APM.
- `resolve`: compute the hull, write the lock, print the tree and the skills prose mentions outside the hull.
- `build [--no-install | --into <dir>]`: resolve, vendor the hull patched and renamed into `.apm/skills/`, deploy
  through APM. `--into <dir>` writes the skills and the lock into an empty `<dir>` instead, never touching the
  package or APM.
- `update [source…] [--dry-run]`: move each git source's `ref` to its branch tip, if the hull still resolves and every
  patch still applies there.
- `tree [--format text|mermaid] [--link]`: print the hull, writing nothing; `--link` gives a mermaid.live URL.
- `why <skill>`: print the paths from the entries that reach a skill, and its upstream folder.
- `add <skill-id>…`, `remove <skill-id>…`: change `entries`, keeping the file's comments, once the result resolves.
- `rename <skill-id> <name>`: set a skill's deployed name; the name it would deploy as without a key undoes it.
- `bind <alias>/<name> <skill-id>|false`: resolve `<name>` from that source to the skill, or to no reference.
- `unbind <alias>/<name>`: remove that bind, so `<name>` resolves by default again.
- `help [command]`, or `--help` on any command: explain it.

## Config

`skill-graft.toml`, in the package:

```toml
entries = ["mp/tdd", "mp/implement", "own/chisel"]
reserved = ["review"]

[sources.mp]
git = "https://github.com/mattpocock/skills.git"
branch = "main"  # optional; defaults to the remote's default branch
ref = "<sha>"
prefix = "mp-"   # optional; every skill of `mp` deploys as mp-<name>

[sources.cp]
git = "https://github.com/cursor/plugins.git"
ref = "<sha>"
subdirectory = "pstack/skills"  # optional; read only this folder of the repository

[sources.own]
path = "~/skills"

[rename]
"own/chisel" = "own-chisel"
"mp/tdd" = "tdd"  # wins over the prefix

[bind]
"mp/grilling" = "own/grilling"
"mp/tmp" = false  # `/tmp` from `mp` is not a reference

[patches]
"mp/implement" = ["patches/implement-no-pr.patch"]
```

- `entries`: the skills you ask for. Slash references and Skill tool calls (`Skill(x)`, or "call the Skill tool
  with `x`") pull in the rest of the hull; prose mentions only become suggestions.
- `sources`: local folders (`path`) and git repositories (`git`), read at the commit `ref` names.
- `subdirectory`: a git source is read only in this folder, as if it were the repository's root, for a repository
  holding several plugins whose skills share names. It must be a real folder at the commit read, or the command
  fails; `update` then leaves `ref` where it is. The lock still records each skill's `upstream` relative to the
  repository's root.
- `prefix` and `[rename]`: a skill deploys as its `[rename]` value, else its source's prefix before its name,
  else its name. Carried into its folder, `name:` and every reference.
- `[bind]`: settles which skill a reference means when several sources have one of that name, or with `false`
  makes it no reference at all.
- `[patches]`: unified diffs, applied before renames, so a patch can change what a skill calls (see
  [Writing a patch](#writing-a-patch)).
- `reserved`: deployed names to refuse, on top of the harness built-ins skill-graft warns about.

## A package for one project

`skill-graft init` creates your package, `~/.apm/skill-graft/`, deployed for you in every project. For skills a
team shares through one repository, run `skill-graft init --project` in its root (which needs a harness folder
such as `.claude/`, or APM refuses): it creates `.apm/skill-graft/` there and registers it in the project's
`apm.yml`. Every command then acts on the nearest `.apm/skill-graft/` above the working folder, and on
`~/.apm/skill-graft/` when there is none.

Commit the whole `.apm/skill-graft/`, vendored skills included, with `apm.yml` and `apm.lock.yaml`. Teammates
then need only APM: `apm install` deploys the skills, and only whoever changes them runs skill-graft. Keep path
sources inside the project (`path = "../../skills"`) and the rest git sources: the lock then records them
relative to the package and reads the same on every machine; a path outside the project is recorded absolute.

## Checking a package

skill-graft finds references by their form alone, so it misses "run the grilling skill", takes `/tmp` for a call,
and can rewrite a word a prefix happens to match. The `graft-check` skill, in this repository's `skills/`, has an
agent read the built skills for those mistakes. Install it like any other skill, with the lines `init` writes
commented out into `skill-graft.toml`:

```toml
[sources.skill-graft]
git = "https://github.com/remigius42/skill-graft.git"
subdirectory = "skills"
```

```sh
skill-graft update skill-graft
skill-graft add skill-graft/graft-check
skill-graft build
```

Until that `update` sets the source's `ref`, every `build` fails, not only graft-check's.

Run it in your harness as `/graft-check`, or `/graft-check mp/tdd` to check only some skills; it runs only when
you ask. It builds into a temporary folder with `build --into`, compares each skill's upstream text with its
vendored copy, and reports missed and false references, references resolved to the wrong skill, wrong or missed
rewrites, and relative links vendoring broke. For each finding it proposes `add`, `bind`, `unbind` or a patch,
and applies it only once you accept. It never deploys: when the package would change, it tells you to run
`skill-graft build`. It reads lock `version` 1 only; for a newer lock, update the source you installed it from.

## Writing a patch

A patch is a unified diff against the skill's upstream folder, which `skill-graft why <skill>` prints on its last
line. No command writes one; in a shell (a project package keeps its patches in its own `.apm/skill-graft/`):

```sh
upstream="$(skill-graft why mp/implement | sed -n 's/^upstream: //p')"
cd "$(mktemp -d)"
cp -rL "$upstream" base && rm -rf base/.git
# Only for a skill that already has patches: apply them first, in order.
(cd base && git apply -p1 ~/.apm/skill-graft/patches/first.patch)
cp -r base edited
"$EDITOR" edited/SKILL.md
LC_ALL=C diff -ruN base/ edited/ > ~/.apm/skill-graft/patches/second.patch
```

Then list it, after the skill's earlier patches:

```toml
[patches]
"mp/implement" = ["patches/first.patch", "patches/second.patch"]
```

`diff` needs `-N`, or added and deleted files are lost; skill-graft refuses such a patch, and binary changes,
by the lines `diff` writes for them in English: hence `LC_ALL=C`. A
patch must not change the skill's `name:`: use `[rename]`. When `update` finds that a patch no longer applies at
a new commit, it keeps the old `ref` and names the upstream folder at the new commit: redo the patch against
it, then run `update` again.

## Contributing

Report bugs and suggest ideas in [GitHub issues](https://github.com/remigius42/skill-graft/issues). To change the
code, see [CONTRIBUTING.md](CONTRIBUTING.md).

This is a personal exploration project with best-effort maintenance. Responses to issues or pull requests may be
slow, and changes that don't align with the project's direction are unlikely to merge.

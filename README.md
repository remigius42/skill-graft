# [skill-graft](https://github.com/remigius42/skill-graft)

[![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fremigius42%2Fskill-graft%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the
whole graph, applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm)
to deploy into Claude Code, opencode, and the other harnesses APM supports.

Skills call each other (`/grilling`, "call the Skill tool with `domain-modeling`"), so taking one skill means
taking every skill it reaches. Installing a whole collection is fine for a large model, but on a smaller one the
full skill set crowds the context, and taking only a subset by hand means tracing those calls yourself, skill by
skill. skill-graft computes that hull, the skills you ask for plus every skill they call, and deploys only those
skills. Renames
come with it: a skill named like a harness built-in (`code-review`) shadows it or is shadowed by it, and renaming
one skill by hand misses the other skills that call it by name.

Status: beta.

## Commands

- `init [--project]`: create the package, `~/.apm/skill-graft/` (or `./.apm/skill-graft/`), and register it with APM.
- `resolve`: compute the hull, write the lock, print the tree and the skills prose mentions outside the hull.
- `build [--no-install]`: resolve, vendor the hull patched and renamed into `.apm/skills/`, deploy through APM.
- `update [source…] [--dry-run]`: move each git source's `ref` to its branch tip, if the hull still resolves there.
- `tree [--format text|mermaid] [--link]`: print the hull, writing nothing; `--link` gives a mermaid.live URL.
- `why <skill>`: print the paths from the entries that reach a skill, and its upstream folder.
- `add <skill-id>…`, `remove <skill-id>…`: change `entries`, keeping the file's comments, once the result resolves.
- `rename <skill-id> <name>`: set a skill's deployed name; the name it would deploy as without a key undoes it.
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
- `prefix` and `[rename]`: a skill deploys as its `[rename]` value, else its source's prefix before its name,
  else its name. Carried into its folder, `name:` and every reference.
- `[bind]`: settles which skill a reference means when several sources have one of that name, or with `false`
  makes it no reference at all.
- `[patches]`: unified diffs, applied before renames, so a patch can change what a skill calls (see
  [Writing a patch](#writing-a-patch)).
- `reserved`: deployed names to refuse, on top of the harness built-ins skill-graft warns about.

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

## Development

See [docs/development.md](docs/development.md).

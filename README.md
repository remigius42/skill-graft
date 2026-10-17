# skill-graft

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

Status: early. `skill-graft init` and `skill-graft build` vendor entries from local folders and from git repositories,
read at the commit `ref` names, and deploy them through APM; `skill-graft update` moves each git source's `ref` to its
branch tip. `build` follows slash references and Skill tool calls (`Skill(x)`, or "call the Skill tool with `x`")
to the whole hull (prose mentions only become suggestions), applies `[rename]` to folders,
`name:` and every reference, and checks deployed names against reserved ones; it applies `[patches]` before any of that,
so a patch can change what a skill calls. `skill-graft resolve` shows the tree and writes the lock, then lists the
skills prose mentions outside the hull (`build` and `update` only count them); `skill-graft tree`
shows it and writes nothing, as text or, with `--format mermaid`, as a Mermaid flowchart (`--link` prints a mermaid.live
URL that holds it); `skill-graft why <skill>` shows the paths from the entries that reach a skill.
`skill-graft add` and `remove <skill-id>…` change the entries in `skill-graft.toml`, and `rename <skill-id> <name>` a
skill's deployed name (its own name undoes it), keeping the file's comments, once the result resolves.
`skill-graft help [command]`, or `--help` on any command, explains each.

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

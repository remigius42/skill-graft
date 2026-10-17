# skill-graft

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the
whole graph, applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm)
to deploy into Claude Code, opencode, and the other harnesses APM supports.

Renames are the reason it exists: a skill named like a harness built-in (`code-review`, `research`,
`prototype`) shadows it or is shadowed by it, and renaming one skill by hand misses the other skills that call
it by name.

Status: early. `skill-graft init` and `skill-graft build` vendor entries from local folders and from git repositories,
read at the commit `ref` names, and deploy them through APM; `skill-graft update` moves each git source's `ref` to its
branch tip. `build` follows slash, Skill tool and prose references to the whole hull, applies `[rename]` to folders,
`name:` and every reference, and checks deployed names against reserved ones; it applies `[patches]` before any of that,
so a patch can change what a skill calls. `skill-graft resolve` shows the tree and writes the lock; `skill-graft tree`
shows it and writes nothing, as text or, with `--format mermaid`, as a Mermaid flowchart (`--link` prints a mermaid.live
URL that holds it); `skill-graft why <skill>` shows the paths from the entries that reach a skill.
`skill-graft add` and `remove <skill-id>…` change the entries in `skill-graft.toml`, and `rename <skill-id> <name>` a
skill's deployed name (its own name undoes it), keeping the file's comments, once the result resolves.
`skill-graft help [command]`, or `--help` on any command, explains each.

## A package for one project

`skill-graft init` creates your package, `~/.apm/skill-graft/`, deployed for you in every project. For skills a
team shares through one repository, run `skill-graft init --project` in its root (which needs a harness folder
such as `.claude/`, or APM refuses): it creates `.apm/skill-graft/` there and registers it in the project's
`apm.yml`. Every command then acts on the nearest `.apm/skill-graft/` above the working folder, and on
`~/.apm/skill-graft/` when there is none.

Commit the whole `.apm/skill-graft/`, vendored skills included, with `apm.yml` and `apm.lock.yaml`. Teammates
then need only APM: `apm install` deploys the skills, and only whoever changes them runs skill-graft.

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

# skill-graft

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the
whole graph, applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm)
to deploy into Claude Code, opencode, and the other harnesses APM supports.

Renames are the reason it exists: a skill named like a harness built-in (`code-review`, `research`,
`prototype`) shadows it or is shadowed by it, and renaming one skill by hand misses the other skills that call
it by name.

Status: early. `skill-graft init` and `skill-graft build` vendor entries from local folders and from git
repositories, read at the commit `ref` names, and deploy them through APM; `skill-graft update` moves each
git source's `ref` to its branch tip. `build` follows slash, Skill tool and prose references to the whole hull,
applies `[rename]` to folders, `name:` and every reference, and checks deployed names against reserved ones;
it applies `[patches]` before any of that, so a patch can change what a skill calls. `skill-graft resolve`
shows the tree and writes the lock.

## Writing a patch

A patch is a unified diff against the skill's upstream folder, which the lock records as `upstream`. No command
writes one; in a shell, with `upstream` set to that folder:

```sh
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

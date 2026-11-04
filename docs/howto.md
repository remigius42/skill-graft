# How to

Common tasks with skill-graft, once it is [installed](../README.md#installation). Terms are defined in
[CONTEXT.md](../CONTEXT.md); every command and config key is listed in the [README](../README.md#commands).

## Add a source and review what it brings

The README's [Usage](../README.md#usage) walks through it. Once added, `skill-graft why <skill>` says which entry pulls
a skill in, and `skill-graft tree` shows the whole hull.

## Edit the config by hand

After editing `skill-graft.toml` or a patch by hand, run `skill-graft resolve` before `deploy`, previewing it first with
`skill-graft resolve --dry-run --diff-file review.diff`: `deploy` deploys only what the lock records, and names
`resolve` when the config or a patch differs from it. An edit to a vendored copy in `.apm/skills/` is refused too; move
it into a patch, or delete the folder to vendor it again.

## Update a source

To move `mp` to its new tip, review what would change first:

```sh
skill-graft update mp --dry-run --diff-file review.diff # write each changed skill's text as deployed
skill-graft update mp --expect <hull-digest>            # the `apply:` line the dry run printed
skill-graft deploy
```

Read `review.diff` in an editor, never by printing it to a terminal: it is untrusted text ([security](security.md)). The
`apply:` line updates to exactly the hull you read; a push, a path source's edit, a patch or a rename since then makes
it refuse.

## Write a patch

Patch a skill to drop a step you do not want, point it at your own tooling, or change which skill it calls, and keep
taking its upstream's updates. Patches apply before renames, so a patch never mentions a deployed name, and `update`
checks that each still applies at the new commit.

A patch is a unified diff against the skill's upstream folder, which `skill-graft why <skill>` prints on its last line.
No command writes one.

First check that your git config has no `apply.*` setting: `git config --get-regexp '^apply\.'` prints nothing.
skill-graft's own `git apply` ignores your git config, so such a setting would give `base/` text that skill-graft never
sees, and the new patch would not apply to it. Then, in a shell (a project package keeps its patches in its own
`.apm/skill-graft/`):

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

Then list the patch, after the skill's earlier ones:

```toml
[patches]
"mp/implement" = ["patches/first.patch", "patches/second.patch"]
```

`skill-graft resolve --dry-run --diff-file review.diff` writes the patched skill as it would deploy to `review.diff`;
read it in an editor, then run `skill-graft resolve`.

`diff` needs `-N`, or added and deleted files are lost; skill-graft refuses such a patch, and binary changes, by the
lines `diff` writes for them in English: hence `LC_ALL=C`. A file such a patch leaves empty is deleted, with any folder
that leaves empty, as `-N` writes a deleted file as one emptied; so any `diff`, GNU or the BSD one of macOS, deletes
alike. A `git diff` patch applies as git applies it. A patch must not change the skill's `name:`: use `[rename]`.

## Redo a patch that no longer applies

When `update` finds that a patch no longer applies at a new commit, it keeps the old `ref` and names, for each failing
skill, its upstream folder at the new commit (`redo it against <folder>`). `update --dry-run` fetches nothing to the
cache, so it names no folder: it says to run `update` without `--dry-run` to fetch the tip; that run fails on the same
hunks, writing nothing but the cache.

Redo the patch as in [Write a patch](#write-a-patch), but with that folder as `upstream`, not the one `why` prints:
`why` reads the old `ref`. Apply the skill's earlier patches to it first, then run `update` again.

## Share skills through a project

`skill-graft init` creates your package, `~/.apm/skill-graft/`, deployed for you in every project. For skills a team
shares through one repository, run `skill-graft init --project` in its root (which needs a harness folder such as
`.claude/`, or APM refuses): it creates `.apm/skill-graft/` there and registers it in the project's `apm.yml`. Every
command then acts on the nearest `.apm/skill-graft/` above the working folder, and on `~/.apm/skill-graft/` when there
is none.

Commit the whole `.apm/skill-graft/`, vendored skills and its `.gitattributes` included, with `apm.yml` and
`apm.lock.yaml`; `.gitattributes` keeps git from changing the vendored skills' line endings, which `deploy` would refuse
as edits. Teammates then need only APM: `apm install` deploys the skills, and only whoever changes them runs
skill-graft. Keep path sources inside the project (`path = "../../skills"`) or under your home folder
(`path = "~/skills"`), and the rest git sources: the lock then records them relative to the package, or as written, and
reads the same on every machine. Any other path, such as `/opt/skills`, `../shared` or `~/x/../skills`, is recorded
absolute, and every command that writes the project's own lock warns of it.

## Check a package with graft-check

skill-graft finds references by their form alone, so it misses "run the grilling skill", takes `/tmp` for a call, and
can rewrite a word a prefix happens to match. The `graft-check` skill, this repository's
[`skills/graft-check/`](../skills/graft-check/SKILL.md), has an agent read the vendored skills for those mistakes.
Install it like any other skill, with the lines `init` writes commented out into `skill-graft.toml`:

```toml
[sources.skill-graft]
git = "https://github.com/remigius42/skill-graft.git"
subdirectory = "skills"
```

```sh
skill-graft update skill-graft
skill-graft add skill-graft/graft-check
skill-graft deploy
```

Until that `update` sets the source's `ref`, every `deploy` fails, not only graft-check's.

Run it in your harness as `/graft-check`, or `/graft-check mp/tdd` to check only some skills; it runs only when you ask.
It deploys into a temporary folder with `deploy --into`, and has one reader per skill compare its upstream text with its
vendored copy. The readers report missed and false references, references resolved to the wrong skill, wrong or missed
rewrites, and relative links vendoring broke. For each finding it proposes `add`, `bind`, `unbind` or a patch, and
applies it only once you accept; a patch is written by a confined patcher, and you read its diff before it goes into the
package. It never runs APM: when the package would change, it tells you to run `skill-graft deploy`. It reads lock
`version` 1 only; for a newer lock, update the source you installed it from.

`[check]` in `skill-graft.toml` sets how far its readers and patcher may go: turns and spend in USD each, and how many
readers run at once; its keys and defaults are in the README's [Config](../README.md#config), and
[Limits](security.md#limits) says what reaching one does.

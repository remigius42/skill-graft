---
name: graft-check
description: Checks a skill-graft package for references its build got wrong. Use only when the user asks for it.
disable-model-invocation: true
---

# graft-check

`/graft-check [skill-id…]` reviews how skill-graft read the **Skills** of the nearest **Package** and proposes config
that fixes what it misread. With **Skill IDs**, it checks those **Hull** **Skills** only; without, the whole **Hull**.

skill-graft finds **References** by their form alone. Your job is the reading it cannot do: whether each one, in its
sentence, means what skill-graft took it for. Every fix lands in the **Package**'s `skill-graft.toml` or a patch file;
deploying stays the user's own `skill-graft build`.

## Terms

- **Skill ID**: `<alias>/<name>`, the **Source** alias and the **Skill**'s name.
- **Reference**: a name skill-graft took for a **Skill**: slash (`/<name>`), Skill tool (`Skill(<name>)`), or prose (a
  name in a code span, or a bare hyphenated name). A slash or Skill tool one resolves in its own **Source** first, else
  in exactly one other; a prose one only in its own.
- **Hull**: the **Entries** (the **Skill IDs** in `entries`) plus every **Skill** their slash and Skill tool
  **References** reach.
- **Bind**: `[bind]` `"<alias>/<name>" = "<skill id>"` or `false`. It decides every **Reference** to that name from
  that **Source**, in every form; `false` makes the name no **Reference** at all. `<alias>` is the **Source** of the
  **Skill** holding the **Reference**, not of its target: `/<name>` in `a/x` resolving to `b/<name>` is bound as
  `a/<name>`.
- **Deployed name**: a **Skill**'s name once built, set by `[rename]` or a **Source**'s `prefix`. Every **Reference** to
  it is rewritten to it.
- **Upstream**: a **Skill** as its **Source** has it, before any **Patch**.
- **Patch**: a unified diff against the **Upstream** folder, listed under `[patches]`, applied before **References**
  resolve.

## 1. Throwaway build

Every build in this skill is a throwaway: a new folder from `mktemp -d`, then `skill-graft build --into` it. Run them
as two commands:

```sh
mktemp -d
skill-graft build --into <folder>
```

- The first stderr line, `skill-graft: package: <path>`, names the **Package**.
- A non-zero exit ends the **Check** with the build's error.
- Read the lock, `skill-graft.lock` in `<folder>`. Its `version` must be 1. Any other value ends the **Check**; a
  higher one means this graft-check is older than the skill-graft that wrote the lock: tell the user to run
  `skill-graft update` on the **Source** they installed graft-check from, in the **Package** that installed it, then
  `skill-graft build` there, and to start a new session.

Done when you hold the **Package** path and a version 1 lock.

## 2. Inputs

An argument that is no `id` in the lock's `[[skills]]` ends the **Check**: name it, and list the ids.

From the lock, for each **Skill** to check (`[[skills]]`, or only the arguments):

- **Vendored copy**: `<folder>/.apm/skills/<deployed name>/`, the `deployed` key, else the name.
- **Upstream folder**: the **Source**'s root joined with the **Skill**'s `upstream`.
  - A path **Source**'s root is `[sources.<alias>] path`; a relative one is relative to the **Package**.
  - A git **Source**'s root: run `skill-graft why <skill id>` for one of its **Skills**; the last line is
    `upstream: <absolute folder>`; take the lock's `upstream` off its end. Once per git **Source**.
- **Patches**: each file in the **Skill**'s `patches`, relative to the **Package** unless absolute or starting with
  `~`. Read them as text; the lines they change are intended.
- **Written names**: `skill-graft tree` prints each edge as `<target> (<as written>[, prose][, bind])`, the target
  followed by `as <deployed name>` when renamed. It shows one edge per target and kind, the first written name, and a
  prose edge only when rewritten; the lock's `[[edges]]` hold targets only.

Done when every **Skill** to check has its vendored copy, **Upstream** folder and patches, and you hold the tree.

## 3. Check

Give each **Skill** to check its own subagent: its **Skill ID**, vendored copy, **Upstream** folder, patch files, the
lock's path, this file's path with "read its Kinds section", and the report shape below. Without subagents, check the
**Skills** one by one yourself. Meanwhile, judge **wrong target** for each target the tree shows from a checked
**Skill**, at every use in its **Upstream** text of a name that resolves there: the target's own name, and each
`[bind]` key of that **Source** in `skill-graft.toml` bound to it.

A subagent reports every finding of the per-**Skill** kinds, or `none`:

```text
skill: <skill id>
file: <path in the skill folder>
text: <the line, quoted>
kind: missed | false | rewrite | link
why: <one sentence>
```

Done when every checked **Skill** has a report and every use of those names has a **wrong target** verdict.

## Kinds

Read each **Skill**'s Markdown files in its **Upstream** folder and its vendored copy, sentence by sentence. A finding
is one of five kinds; the first four are judged per **Skill**:

- **missed**: words that call a **Skill** in a form skill-graft does not read: "run the `<name>` skill", "hand off to
  `<name>`". Its **Skill** stays out of the **Hull**, or keeps its old name after a rename.
- **false**: a slash or Skill tool **Reference** that names no **Skill**, so it pulls one into the **Hull** or
  skill-graft warns that none matches: `` `GET /<route>` ``, a path `/<folder>` in prose. A prose one is a **rewrite**
  when the build changed it, and otherwise no finding.
- **rewrite**: compare the **Upstream** text, plus its patches' lines, with the vendored copy. Each remaining change
  must be a **Reference** rewritten to its **Deployed name**. Wrong: a word changed that names no **Skill** there, such
  as a hyphenated word that happens to match a renamed **Skill**'s name. Missed: a renamed **Skill**'s name left as it
  was where it means that **Skill**.
- **link**: a relative link or path that works in the **Upstream** folder and breaks in the vendored copy:
  `../<other>/<file>.md` into another **Skill**'s folder, now under another name or not vendored.
- **wrong target**, judged from the tree's targets at every use of their names: a **Reference** whose written name,
  read in its **Upstream** sentence, means another **Skill** than its target: `/<name>` from **Source** `a` means a
  **Skill** `a` lacks, and resolved to an unrelated `b/<name>`; or a **Bind** sends it astray.

## 4. Report

List each finding with its **Skill**, file, text, kind, and a proposed fix:

| Kind         | Fix                                                                                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| missed       | a **Patch** writing `/<name>`: it pulls the **Skill** in and follows its **Deployed name**; `skill-graft add <skill id>` when it deploys under its own name |
| false        | `skill-graft bind <alias>/<name> false`, or a **Patch**                                                                                                     |
| wrong target | `skill-graft bind <alias>/<name> <skill id>`, `skill-graft unbind <alias>/<name>` for a wrong **Bind**, or a **Patch**                                      |
| rewrite      | `skill-graft bind <alias>/<name> false` for a word, or a **Patch**                                                                                          |
| link         | a **Patch** of the link                                                                                                                                     |

A **Bind** is source-wide. Before proposing one for `<name>` from `<alias>`, search the **Upstream** text, plus the
lines its patches add, of every **Hull** **Skill** of `<alias>` for `<name>` in each form: `/<name>`, `Skill(<name>)`,
the name in a code span, the bare name. Propose the **Bind** only when every match needs it; when some are right,
propose a **Patch** of the **Skill** holding the wrong one.

With no finding, say the **Check** found nothing and go to step 6.

Done when every finding is listed with its fix.

## 5. Fixes

Take the fixes one at a time: ask, and apply only on yes.

- `add`, `bind` and `unbind` write only a config that resolves. Before a `bind` or `unbind`, note the key's value.
- A **Patch**, with `<package>` the **Package** path and `<n>` a new patch name:
  1. `cp -rL <upstream folder> base && rm -rf base/.git` in a new `mktemp -d` folder.
  1. Apply the **Skill**'s patch files (step 2) in order: `(cd base && git apply -p1 <absolute patch file>)`.
  1. `cp -r base edited`, edit the files in `edited/`, keeping `name:` as it is.
  1. `mkdir -p <package>/patches/`, then `LC_ALL=C diff -ruN base/ edited/ > <package>/patches/<n>.patch`; its exit
     code 1 means it wrote a diff.
  1. Append `"patches/<n>.patch"` to the **Skill**'s list under `[patches]` in the **Package**'s `skill-graft.toml`,
     creating the key or the table if missing. Note which you created.

After each applied fix, make a throwaway build (step 1) into a new folder and compare its lock's `[[skills]]` ids with
the previous build's. Name every **Skill** that left or joined the **Hull**.

When that build fails, undo the fix and show the error:

- `add`: `skill-graft remove` the same **Skill IDs**.
- `bind` or `unbind`: `skill-graft bind` the key to its noted value, or `skill-graft unbind` it if it had none.
- A **Patch**: delete its file and remove its own item from the list; the key and the `[patches]` table only if you
  created them.

Done when every proposed fix is applied or declined.

## 6. Close

Compare the first throwaway build's folder with the **Package**: `diff -rq <folder>/.apm/skills <package>/.apm/skills`.
A missing `<package>/.apm/skills` counts as a difference: the commands that edit config write the lock and leave the
vendored copies behind.

- A fix was accepted, or the folders differ: end by telling the user to run `skill-graft build`.
- Otherwise: say the **Package** is as its config builds it, and that whether APM deployed it is not checked.

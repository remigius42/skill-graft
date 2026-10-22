## Purpose

The `graft-check` skill: a **Check** the user runs on a built **Package**, in which an agent reads the **Skills**
for what form-based resolution gets wrong and proposes **Binds**, **Entries** and **Patches** to fix it.

## ADDED Requirements

### Requirement: Installed as a skill of this repository

This repository SHALL hold the skill at `skills/graft-check/SKILL.md`, a **Skill** named `graft-check`, so a **Source**
of the repository has it as `<alias>/graft-check`. Its text SHALL name no **Skill** but itself in slash or Skill tool
form, since those resolve in every **Source**, and hold no prose **Reference** to another **Skill** of the repository
(its own name, as in its usage line, is no **Reference**), so its **Hull** is itself alone in any **Package** and
resolving it gives no warning and no suggestion.

#### Scenario: Alone in its hull

- **WHEN** a git **Source** `sg` with `subdirectory = "skills"` holds a commit of this repository's `skills/`
  folder, and `entries = ["sg/graft-check"]`
- **THEN** `skill-graft resolve` succeeds, the **Hull** is `sg/graft-check` alone, and it prints no warning and
  no suggestion

### Requirement: Invoked only by the user

The skill's front matter SHALL set `disable-model-invocation: true` and an `argument-hint` naming the optional
`<alias>/<name>` arguments, and its description SHALL say it runs only when the user asks for it. Given **Skill IDs** as
arguments, it SHALL check only those **Hull** **Skills**; without arguments, the whole **Hull**. An argument that is no
**Skill ID** of the **Hull** SHALL end the **Check**, naming it and listing the **Hull**'s **Skill IDs**.

#### Scenario: Front matter

- **WHEN** `skills/graft-check/SKILL.md` is parsed
- **THEN** its front matter has `name: graft-check`, `disable-model-invocation: true` and an `argument-hint` with
  `<alias>/<name>`, and its description says it runs only when the user asks

#### Scenario: Scoped

- **WHEN** the user runs `/graft-check mp/tdd`
- **THEN** the report covers `mp/tdd` only

#### Scenario: Unknown argument

- **WHEN** the user runs `/graft-check mp-tdd`, the **Deployed name** rather than the **Skill ID**
- **THEN** the skill names `mp-tdd`, lists the **Hull**'s **Skill IDs**, and checks nothing

### Requirement: Builds before reading

The skill SHALL first make a new, empty folder under the system's temporary folder and run `skill-graft build --into`
with it, reading the **Package** from the `package:` line. A failing build SHALL end the **Check** with the build's
error. It SHALL then read the lock and the vendored copies in that folder, and each **Skill**'s **Upstream** folder:
under a path **Source**'s folder as the lock records it, and for a git **Source** under its root, found once through
`skill-graft why` on one of its **Skills**. For a **Skill** the lock lists `patches` for, the skill SHALL read those
patch files and count the lines they change as intended, applying nothing. It SHALL take the targets from
`skill-graft tree` and judge each at every use, in the **Upstream** text, of its own name and of each `[bind]` key of
that **Source** bound to it, since the tree shows one edge per target, kind and **Bind**, and a prose edge only when
rewritten. The **Package**'s own `.apm/skills/` and lock SHALL change only through accepted fixes.

#### Scenario: Build fails

- **WHEN** `skill-graft build --into <folder>` exits non-zero
- **THEN** the skill reports its error and checks nothing

#### Scenario: Patched lines are intended

- **WHEN** the lock lists `patches` for `mp/x`, and one of them changes a line of its `SKILL.md`
- **THEN** that line is not reported as a rewrite of the wrong text

#### Scenario: Looking changes nothing

- **WHEN** the user runs `/graft-check` and declines every fix
- **THEN** the **Package**'s `skill-graft.toml`, `skill-graft.lock` and `.apm/skills/` keep their bytes

### Requirement: Lock version

The skill SHALL read lock `version = 1` only; any other version SHALL stop it. A higher one SHALL come with the
advice to run `skill-graft update` on the **Source** the user installed `graft-check` from, in the **Package**
that installed it, then `skill-graft build` there, and a new session.

#### Scenario: Newer lock

- **WHEN** the lock has `version = 2`
- **THEN** the skill stops and says to update the **Source** `graft-check` was installed from, in its own
  **Package**, run `skill-graft build` there, and start a new session

### Requirement: What it reports

The skill SHALL report the findings as a table, one row per finding with the **Skill**, the file, the text, its kind,
and a proposed fix. The kinds SHALL be: a missed **Reference**, a false **Reference**, a **Reference** resolved to
the wrong **Skill**, a rewrite of the wrong text or a missed one, and a relative link that the vendored copy breaks.

#### Scenario: Planted defects

- **WHEN** a **Package**'s **Hull** holds one defect of each kind
- **THEN** the report names each of them with its kind

#### Scenario: Nothing found

- **WHEN** the **Hull** has none of these defects
- **THEN** the skill says it found nothing and proposes no fix

### Requirement: Fixes fit their scope

A **Bind** applies to every **Reference** to its name from its **Source**. The skill SHALL propose a **Bind** only when
that is what every such **Reference** needs, judged by searching the **Upstream** text of that **Source**'s **Hull**
**Skills**, plus the lines their **Patches** add, for the name (the lock's edges name no **Reference**); when only some
of them are wrong, it SHALL propose a **Patch** of the **Skill** that holds the wrong one.

#### Scenario: One false match among real calls

- **WHEN** `mp/a` calls `/grill` and `mp/b` writes `` `GET /grill` ``, an HTTP route, not a call
- **THEN** the skill proposes a **Patch** of `mp/b`, not `skill-graft bind mp/grill false`

### Requirement: Fixes only once accepted

The skill SHALL apply a fix only after the user accepts it, one fix at a time, through `skill-graft add`,
`skill-graft bind` or `skill-graft unbind`, or as a **Patch** written by the README's recipe with the **Package**
from the `package:` line in place of its `~/.apm/skill-graft/`. After each it SHALL build again `--into` another
new, empty folder and name every **Skill** that left or joined the **Hull** since the previous build. It SHALL NOT edit
the vendored **Skills**.

#### Scenario: Declined

- **WHEN** the user declines a proposed **Bind**
- **THEN** `skill-graft.toml` keeps its bytes

#### Scenario: A skill leaves the hull

- **WHEN** an accepted fix drops `mp/grill` from the **Hull**
- **THEN** the skill says `mp/grill` left the **Hull**

#### Scenario: A skill joins the hull

- **WHEN** the user accepts `skill-graft add mp/notes`, and `mp/notes` calls `/todo`
- **THEN** the skill says `mp/notes` and `mp/todo` joined the **Hull**

### Requirement: A failed fix is undone

When the build after an accepted fix fails, the skill SHALL undo that fix and show the error. After `skill-graft add`
it SHALL run `skill-graft remove` on the same **Skill IDs**; after `skill-graft bind` or `skill-graft unbind` it SHALL
restore the key's value from before the fix, or unbind a key that had none. After a **Patch** it SHALL delete the
patch file and remove only its own item from the **Skill**'s `[patches]` list, the key only if the skill created it,
and the `[patches]` table only if the skill created that, leaving the user's earlier **Patches** and
`skill-graft.toml` otherwise as it was.

#### Scenario: Bind restored

- **WHEN** `[bind]` has `"mp/g" = "own/notes"`, the user accepts `skill-graft bind mp/g mp/grill`, and the build
  fails
- **THEN** `[bind]` again has `"mp/g" = "own/notes"`

#### Scenario: Earlier patches kept

- **WHEN** `[patches]` has `"mp/x" = ["patches/first.patch"]`, the skill appends `patches/second.patch`, and the
  build fails
- **THEN** `[patches]` again has `"mp/x" = ["patches/first.patch"]`, and `patches/second.patch` is gone

### Requirement: Never deploys

The skill SHALL NOT run `skill-graft build` without `--into`, nor `apm`. It SHALL end by telling the user to run
`skill-graft build` when a fix was accepted, or when its first build's `.apm/skills/` differs from the **Package**'s, so
an in-place build would change the vendored copies. Commands that write only the lock (`add`, `remove`, `rename`,
`bind`, `unbind`, `update`, `resolve`) leave the **Package**'s lock current and its vendored copies behind, so the
comparison is of the folders, not the locks. A **Package** with no `.apm/skills/` yet differs. Otherwise it SHALL say
the **Package** is as the config builds it, and that it cannot tell whether APM deployed that.

#### Scenario: After a fix

- **WHEN** the user accepted a fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Source changed, every fix declined

- **WHEN** a path **Source**'s **Skill** changed since the last in-place build, and the user declines every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Lock current, vendored copies behind

- **WHEN** the user ran `skill-graft add mp/x` but no `build`, and declines every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Never built

- **WHEN** the **Package** holds no `.apm/skills/` and the user declines every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Nothing to build

- **WHEN** the first build's `.apm/skills/` equals the **Package**'s and the user declines every fix
- **THEN** the skill does not tell the user to run `skill-graft build`

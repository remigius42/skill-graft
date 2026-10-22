## Purpose

The `graft-check` skill: a **Check** the user runs on a built **Package**, in which an agent reads the **Skills**
for what form-based resolution gets wrong and proposes **Binds**, **Entries** and **Patches** to fix it.

## ADDED Requirements

### Requirement: Installed as a skill of this repository

This repository SHALL hold the skill at `skills/graft-check/SKILL.md`, a **Skill** named `graft-check`, so a
**Source** of the repository has it as `<alias>/graft-check`. Its text SHALL hold no slash, Skill tool or prose
**Reference** to any **Skill** the repository holds, so its **Hull** is itself alone and resolving it gives no
warning and no suggestion.

#### Scenario: Alone in its hull

- **WHEN** a **Source** `sg` holds the files this repository tracks under `skills/` and
  `entries = ["sg/graft-check"]`
- **THEN** `skill-graft resolve` succeeds, the **Hull** is `sg/graft-check` alone, and it prints no warning and
  no suggestion

### Requirement: Invoked only by the user

The skill's front matter SHALL set `disable-model-invocation: true`, and its description SHALL say it runs only
when the user asks for it. Given **Skill IDs** as arguments, it SHALL check only those **Hull** **Skills**;
without arguments, the whole **Hull**.

#### Scenario: Front matter

- **WHEN** `skills/graft-check/SKILL.md` is parsed
- **THEN** its front matter has `name: graft-check` and `disable-model-invocation: true`

#### Scenario: Scoped

- **WHEN** the user runs `/graft-check mp/tdd`
- **THEN** the report covers `mp/tdd` only

### Requirement: Builds before reading

The skill SHALL first make a new, empty folder under the system's temporary folder and run
`skill-graft build --into` with it, reading the **Package** from the `package:` line. A failing build SHALL end the
**Check** with the build's error. It SHALL then read the lock and the vendored copies in that folder, and each
**Skill**'s **Upstream** folder, finding each **Source**'s folder once (through `skill-graft why` on one of its
**Skills**) and joining it with the lock's relative `upstream`. The **Package**'s own `.apm/skills/` and lock SHALL
change only through accepted fixes.

#### Scenario: Build fails

- **WHEN** `skill-graft build --into <folder>` exits non-zero
- **THEN** the skill reports its error and checks nothing

#### Scenario: Looking changes nothing

- **WHEN** the user runs `/graft-check` and declines every fix
- **THEN** the **Package**'s `skill-graft.toml`, `skill-graft.lock` and `.apm/skills/` keep their bytes

### Requirement: Lock version

The skill SHALL read lock `version = 1` only; any other version SHALL stop it. A higher one SHALL come with the
advice to run `skill-graft update <alias>` for the **Source** that holds the skill, `skill-graft build`, and a new
session.

#### Scenario: Newer lock

- **WHEN** the lock has `version = 2`
- **THEN** the skill stops and names `skill-graft update` with its own **Source**'s alias

### Requirement: What it reports

The skill SHALL report each finding with the **Skill**, the file, the text, its kind, and a proposed fix. The
kinds SHALL be: a missed **Reference**, a false **Reference**, a **Reference** resolved to the wrong **Skill**, a
rewrite of the wrong text or a missed one, and a relative link that the vendored copy breaks.

#### Scenario: Planted defects

- **WHEN** a **Package**'s **Hull** holds one defect of each kind
- **THEN** the report names each of them with its kind

#### Scenario: Nothing found

- **WHEN** the **Hull** has none of these defects
- **THEN** the skill says it found nothing and proposes no fix

### Requirement: Fixes fit their scope

A **Bind** applies to every **Reference** to its name from its **Source**. The skill SHALL propose a **Bind** only
when that is what every such **Reference** needs, judged by searching the **Upstream** text of that **Source**'s
**Hull** **Skills** for the name (the lock's edges name no **Reference**); when only some of them are wrong, it
SHALL propose a **Patch** of the **Skill** that holds the wrong one.

#### Scenario: One false match among real calls

- **WHEN** `mp/a` calls `/grill` and `mp/b` writes `/grill` as a URL path, not a call
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

### Requirement: A failed patch is undone

When the build after a **Patch** fails, the skill SHALL delete the patch file and remove only its own item from
the **Skill**'s `[patches]` list, and the key only if the skill created it, leaving the user's earlier **Patches**.

#### Scenario: Earlier patches kept

- **WHEN** `[patches]` has `"mp/x" = ["patches/first.patch"]`, the skill appends `patches/second.patch`, and the
  build fails
- **THEN** `[patches]` again has `"mp/x" = ["patches/first.patch"]`, and `patches/second.patch` is gone

### Requirement: Never deploys

The skill SHALL NOT run `skill-graft build` without `--into`, nor `apm`. It SHALL end by telling the user to run
`skill-graft build` when a fix was accepted, or when its first build's lock differs from the **Package**'s, so an
in-place build would change the vendored copies. Otherwise it SHALL say the **Package** is as the config builds
it, and that it cannot tell whether APM deployed that.

#### Scenario: After a fix

- **WHEN** the user accepted a fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Source changed, every fix declined

- **WHEN** a path **Source**'s **Skill** changed since the last in-place build, and the user declines every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Nothing to build

- **WHEN** the first build's lock equals the **Package**'s and the user declines every fix
- **THEN** the skill does not tell the user to run `skill-graft build`

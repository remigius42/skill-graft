## Purpose

The `graft-check` skill: a **Check** the user runs on a built **Package**, in which an agent reads the **Skills**
for what form-based resolution gets wrong and proposes **Binds**, **Entries** and **Patches** to fix it.

## ADDED Requirements

### Requirement: Installed as a skill of this repository

This repository SHALL hold the skill at `skills/graft-check/SKILL.md`, a **Skill** named `graft-check`, so a
**Source** of the repository has it as `<alias>/graft-check`. Its text SHALL hold no slash, Skill tool or prose
**Reference**, so its **Hull** is itself alone and resolving it gives no warning.

#### Scenario: Alone in its hull

- **WHEN** a **Source** `sg` points at this repository's `skills/` folder and `entries = ["sg/graft-check"]`
- **THEN** `skill-graft resolve` succeeds, the **Hull** is `sg/graft-check` alone, and no warning is printed

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

The skill SHALL first run `skill-graft build --no-install` and read the **Package** from its `package:` line. A
failing build SHALL end the **Check** with the build's error. It SHALL then read the lock, each **Skill**'s
**Upstream** folder (as `skill-graft why` prints it) and its vendored copy.

#### Scenario: Build fails

- **WHEN** `skill-graft build --no-install` exits non-zero
- **THEN** the skill reports its error and checks nothing

### Requirement: Lock version

The skill SHALL read lock `version = 1` only. A newer version SHALL stop it, telling the user to run
`skill-graft update <alias>` for the **Source** that holds the skill, `skill-graft build`, and a new session; an
older one SHALL stop it, telling the user to upgrade skill-graft (`uv tool upgrade skill-graft`).

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

### Requirement: Fixes only once accepted

The skill SHALL apply a fix only after the user accepts it, one fix at a time, through `skill-graft add`,
`skill-graft bind` or `skill-graft unbind`, or as a **Patch** written by the README's recipe and listed under
`[patches]`. After each it SHALL run `skill-graft build --no-install`; a **Patch** whose build fails SHALL be
removed again, file and key. It SHALL NOT edit the vendored **Skills**.

#### Scenario: Declined

- **WHEN** the user declines a proposed **Bind**
- **THEN** `skill-graft.toml` keeps its bytes

### Requirement: Never deploys

The skill SHALL NOT run `skill-graft build` without `--no-install`, nor `apm`. When it has applied a fix, it SHALL
end by telling the user to run `skill-graft build` to deploy it.

#### Scenario: After a fix

- **WHEN** the user accepted a fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

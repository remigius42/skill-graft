## MODIFIED Requirements

### Requirement: Fixes only once accepted

The skill SHALL apply a fix only after the user accepts it, one fix at a time, through `skill-graft add`,
`skill-graft bind` or `skill-graft unbind`, or as a **Patch** the user read: written by the patcher in a hardened
**Check**, in the skill's own session in an unhardened one. After adding a **Patch** to `[patches]` it SHALL run
`skill-graft resolve`. After each fix it SHALL build again `--into` another new, empty folder and name every **Skill**
that left or joined the **Hull** since the previous build. It SHALL NOT edit the vendored **Skills**.

#### Scenario: Declined

- **WHEN** the user declines a proposed **Bind**
- **THEN** `skill-graft.toml` keeps its bytes

#### Scenario: A skill leaves the hull

- **WHEN** an accepted fix drops `mp/grill` from the **Hull**
- **THEN** the skill says `mp/grill` left the **Hull**

#### Scenario: A skill joins the hull

- **WHEN** the user accepts `skill-graft add mp/notes`, and `mp/notes` calls `/todo`
- **THEN** the skill says `mp/notes` and `mp/todo` joined the **Hull**

#### Scenario: Patch accepted

- **WHEN** the user accepts a **Patch** of `mp/x`
- **THEN** the skill runs `skill-graft resolve` after adding it to `[patches]`, and only then builds `--into` a new
  folder

### Requirement: A failed fix is undone

When the build after an accepted fix fails, or the `skill-graft resolve` after a **Patch**, the skill SHALL undo that
fix and show the error. After `skill-graft add` it SHALL run `skill-graft remove` on the same **Skill IDs**; after
`skill-graft bind` or `skill-graft unbind` it SHALL restore the key's value from before the fix, or unbind a key that
had none. After a **Patch** it SHALL delete the patch file and remove only its own item from the **Skill**'s `[patches]`
list, the key only if the skill created it, and the `[patches]` table only if the skill created that, leaving the user's
earlier **Patches** and `skill-graft.toml` otherwise as it was, then run `skill-graft resolve` again if its `resolve`
after the **Patch** succeeded.

#### Scenario: Bind restored

- **WHEN** `[bind]` has `"mp/g" = "own/notes"`, the user accepts `skill-graft bind mp/g mp/grill`, and the build fails
- **THEN** `[bind]` again has `"mp/g" = "own/notes"`

#### Scenario: Earlier patches kept

- **WHEN** `[patches]` has `"mp/x" = ["patches/first.patch"]`, the skill appends `patches/second.patch`, and the build
  fails
- **THEN** `[patches]` again has `"mp/x" = ["patches/first.patch"]`, `patches/second.patch` is gone, and the skill ran
  `skill-graft resolve` again

#### Scenario: Patch fails to resolve

- **WHEN** the skill appends `patches/second.patch` to `mp/x`'s list, and `skill-graft resolve` fails on it
- **THEN** `[patches]` again has `mp/x`'s earlier list, `patches/second.patch` is gone, the skill shows the error, and
  it runs no second `resolve`

### Requirement: Never deploys

The skill SHALL NOT run `skill-graft build` without `--into`, nor `apm`. It SHALL end by telling the user to run
`skill-graft build` when a fix was accepted, or when its first build's `.apm/skills/` differs from the **Package**'s, as
after a path **Source**'s **Skill** changed, so an in-place build would change the vendored copies. A **Package** with
no `.apm/skills/` yet differs. Otherwise it SHALL say the **Package**'s vendored copies are as its config builds them,
and to run `skill-graft build` if it has not run since the last change, which the skill cannot tell.

#### Scenario: After a fix

- **WHEN** the user accepted a fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Source changed, every fix declined

- **WHEN** a path **Source**'s **Skill** changed since the last in-place build, and the user declines every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Lock current, vendored copies behind

- **WHEN** the user ran `skill-graft add mp/x` but no `build`, and declines every fix
- **THEN** the skill's last message says the vendored copies are as the config builds them, and to run
  `skill-graft build` if it has not run since the last change

#### Scenario: Never built

- **WHEN** the **Package** holds its lock but no `.apm/skills/`, as after the user deleted it, and the user declines
  every fix
- **THEN** the skill's last message tells the user to run `skill-graft build`

#### Scenario: Never resolved

- **WHEN** the **Package** holds no `skill-graft.lock`, as after `init`
- **THEN** the first build `--into` exits 1 naming `skill-graft resolve`, and the **Check** ends with that error

#### Scenario: Nothing to build

- **WHEN** the first build's `.apm/skills/` equals the **Package**'s and the user declines every fix
- **THEN** the skill does not tell the user to run `skill-graft build` unconditionally, only if it has not run since the
  last change

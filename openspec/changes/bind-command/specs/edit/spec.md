## MODIFIED Requirements

### Requirement: Resolve before writing

`add`, `remove`, `rename`, `bind` and `unbind` SHALL compute the **Hull** of the edited config, as `resolve` does,
before writing anything. Only if that succeeds SHALL they write `skill-graft.toml`, then `skill-graft.lock`, and print
what `resolve` prints. A failure SHALL exit 1 and leave both files unchanged. They SHALL NOT write `.apm/skills/` or
run `apm`. When the command changes no value (every **Skill ID** given is a no-op, or `bind`'s target is the current
value), it SHALL print only its notices, exit 0, and neither resolve nor write anything.

#### Scenario: Edit succeeds

- **WHEN** the user runs `skill-graft add mp/notes` and the edited config resolves
- **THEN** `entries` holds `mp/notes`, the lock is rewritten, the tree is printed, and `.apm/skills/` is unchanged

#### Scenario: Edit fails to resolve

- **WHEN** the user runs `skill-graft add mp/notes` and `mp/notes` calls `/x`, which matches several other
  **Sources** and no **Bind**
- **THEN** it exits non-zero, and `skill-graft.toml` and `skill-graft.lock` keep their bytes

## ADDED Requirements

### Requirement: Bind a name

`bind <alias>/<name> <target>` SHALL set `[bind]."<alias>/<name>"` to `<target>`, a **Skill ID**, or `false` when
`<target>` is the word `false`, replacing an existing value in place or appending a key, and SHALL append a
`[bind]` table at the end of the file when it is absent. A `<target>` equal to the current value, `false`
included, SHALL be a notice and change nothing, once the target is checked.

#### Scenario: New bind

- **WHEN** there is no `[bind]` table, **Entry** `mp/tdd` calls `/grilling`, and the user runs
  `skill-graft bind mp/grilling own/grill`
- **THEN** the file ends with a `[bind]` table holding `"mp/grilling" = "own/grill"`, and the tree shows
  `own/grill` under `mp/tdd`

#### Scenario: Bind to nothing

- **WHEN** **Entry** `mp/tdd` mentions `/tmp` and the user runs `skill-graft bind mp/tmp false`
- **THEN** `[bind]` holds `"mp/tmp" = false`, a TOML boolean, and the unmatched-**Reference** warning about
  `tmp`, printed before the bind, is gone

#### Scenario: Replaced

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"` with a trailing comment, and the user runs
  `skill-graft bind mp/grilling false`
- **THEN** the new file equals the old one with only that value replaced

#### Scenario: Already bound so

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"` and the user runs `skill-graft bind mp/grilling own/grill`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already bound to nothing

- **WHEN** `[bind]` has `"mp/tmp" = false` and the user runs `skill-graft bind mp/tmp false`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already bound to a skill gone upstream

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"`, `own` no longer has `grill`, and the user runs
  `skill-graft bind mp/grilling own/grill`
- **THEN** it exits non-zero naming `own/grill`, and `skill-graft.toml` keeps its bytes

### Requirement: Bind checks its key and target

`bind` SHALL refuse a malformed `<alias>/<name>` or an undeclared alias, and a `<target>` that is neither `false`
nor a **Skill ID** whose **Source** holds that **Skill**, writing nothing. `<name>` need not be a **Skill**. A
**Bind** no **Reference** uses SHALL be written, with the usual unused-bind warning.

#### Scenario: Unknown target

- **WHEN** **Source** `own` has no **Skill** `nope` and the user runs `skill-graft bind mp/grilling own/nope`
- **THEN** it exits non-zero naming `own/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Undeclared alias in the key

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft bind zz/grilling own/grill`
- **THEN** it exits non-zero naming the alias `zz`, and `skill-graft.toml` is unchanged

#### Scenario: Malformed target

- **WHEN** the user runs `skill-graft bind mp/grilling true`
- **THEN** it exits non-zero naming `true`, and `skill-graft.toml` is unchanged

#### Scenario: Unused bind

- **WHEN** no **Hull** **Skill** in `mp` mentions `grill` and the user runs `skill-graft bind mp/grill own/grill`
- **THEN** `[bind]` holds `"mp/grill" = "own/grill"`, and the unused-bind warning names `mp/grill`

### Requirement: Unbind a name

`unbind <alias>/<name>` SHALL delete the key from `[bind]`, leaving the table in place even if empty, so
**References** to `<name>` from that **Source** resolve by default again. A malformed key or an undeclared alias
SHALL be refused as `bind` refuses them, and a key not in `[bind]` SHALL be an error, both writing nothing.

#### Scenario: Unbound

- **WHEN** `[bind]` has only `"mp/grilling" = "own/grill"`, `mp` has `grilling`, **Entry** `mp/tdd` calls
  `/grilling`, and the user runs `skill-graft unbind mp/grilling`
- **THEN** `[bind]` is empty, and the tree shows `mp/grilling` under `mp/tdd`

#### Scenario: Not bound

- **WHEN** `[bind]` has no `"mp/grilling"` and the user runs `skill-graft unbind mp/grilling`
- **THEN** it exits non-zero naming `mp/grilling`, and `skill-graft.toml` is unchanged

#### Scenario: Unbind with an undeclared alias

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft unbind zz/grilling`
- **THEN** it exits non-zero naming the alias `zz`, not saying the key is not bound, and `skill-graft.toml` is
  unchanged

#### Scenario: Unbinding breaks resolution

- **WHEN** `[bind]` has `"mp/x" = "own/x"`, **Entry** `mp/tdd` calls `/x`, `mp` has no `x`, and both `own` and
  `other` have one, and the user runs `skill-graft unbind mp/x`
- **THEN** it exits non-zero, and `skill-graft.toml` and `skill-graft.lock` keep their bytes

## MODIFIED Requirements

### Requirement: Resolve before writing

`add`, `remove`, `rename`, `bind` and `unbind` SHALL compute the **Hull** of the edited config, as `resolve` does,
before writing anything. Only if that succeeds SHALL they write `skill-graft.toml`, then `skill-graft.lock`, and print
what `resolve` prints. A failure SHALL exit 1 and leave both files unchanged; so SHALL an interrupt while the lock is
written, but exit as interrupted. If restoring `skill-graft.toml` fails too, a notice SHALL name it and the error,
and the original error SHALL be the one reported. They SHALL NOT write `.apm/skills/` or run `apm`. When the command
changes no value
(every **Skill ID** given is a no-op, or `bind`'s target is the current value), it SHALL print only its notices, exit
0, and neither resolve nor write anything.

#### Scenario: Edit succeeds

- **WHEN** the user runs `skill-graft add mp/notes` and the edited config resolves
- **THEN** `entries` holds `mp/notes`, the lock is rewritten, the tree is printed, and `.apm/skills/` is unchanged

#### Scenario: Edit fails to resolve

- **WHEN** the user runs `skill-graft add mp/notes` and `mp/notes` calls `/x`, which matches several other
  **Sources** and no **Bind**
- **THEN** it exits non-zero, and `skill-graft.toml` and `skill-graft.lock` keep their bytes

#### Scenario: Lock write interrupted

- **WHEN** the user runs `skill-graft add mp/notes`, the edited config resolves, and the user presses Ctrl-C while
  `skill-graft.lock` is written
- **THEN** `skill-graft.toml` and `skill-graft.lock` keep their bytes

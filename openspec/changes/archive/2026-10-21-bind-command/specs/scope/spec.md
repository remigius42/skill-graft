## MODIFIED Requirements

### Requirement: Commands that write name the package

`init`, `resolve`, `build`, `update`, `add`, `remove`, `rename`, `bind` and `unbind` SHALL print
`skill-graft: package: <absolute path of the Package>` on stderr before the command's own output, in either
**Scope**, including when the command fails after its arguments parsed. `tree`, `why` and `help` SHALL NOT print
it, and neither SHALL a usage error or `init --project` refused in the home folder.

#### Scenario: Build names the package

- **WHEN** the user runs `skill-graft build` in a project with a **Package**
- **THEN** stderr starts with `skill-graft: package: <project>/.apm/skill-graft`

#### Scenario: Read-only command

- **WHEN** the user runs `skill-graft tree`
- **THEN** no `package:` line is printed

#### Scenario: Bind names the package

- **WHEN** the user runs `skill-graft bind mp/tmp false`
- **THEN** stderr starts with `skill-graft: package: <absolute path of the Package>`

#### Scenario: Unbind names the package

- **WHEN** the user runs `skill-graft unbind mp/tmp`
- **THEN** stderr starts with `skill-graft: package: <absolute path of the Package>`

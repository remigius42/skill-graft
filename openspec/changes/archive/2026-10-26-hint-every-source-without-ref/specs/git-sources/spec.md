# Spec Delta

## MODIFIED Requirements

### Requirement: Build needs every ref

`build` SHALL fail when any git **Source** has no `ref`, whether or not an **Entry** uses it, naming every such
alias and telling the user to run the one `skill-graft update` command naming them all. `build` SHALL then write
nothing.

#### Scenario: New git source

- **WHEN** `[sources.mp]` has `git` but no `ref`
- **THEN** `build` exits non-zero naming `mp` and `skill-graft update mp`

#### Scenario: Several new git sources

- **WHEN** `[sources.a]` and `[sources.b]` both have `git` but no `ref`
- **THEN** `build` exits non-zero naming `a`, `b` and `skill-graft update a b`

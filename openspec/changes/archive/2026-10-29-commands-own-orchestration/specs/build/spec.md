## MODIFIED Requirements

### Requirement: Build resolves first

`build` SHALL resolve the **Hull** as `resolve` does before vendoring, and write `skill-graft.lock` once vendoring
succeeded, before running APM. A resolution or vendoring error SHALL leave the lock unchanged. Its warnings come
last, after APM's output, as "Warnings come last" says. `build --into` writes its lock into another folder
instead, as "Build into a folder" says.

#### Scenario: Lock written

- **WHEN** the user runs `build --no-install`
- **THEN** `skill-graft.lock` records the vendored **Hull**

#### Scenario: Vendoring fails

- **WHEN** a copy fails during `build`
- **THEN** `skill-graft.lock` is unchanged

#### Scenario: Warning does not stop build

- **WHEN** an **Entry** calls `/foo` and no **Source** has `foo`
- **THEN** `build` prints the warning and exits 0

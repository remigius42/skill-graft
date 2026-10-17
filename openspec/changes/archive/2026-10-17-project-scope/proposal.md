# Proposal

## Why

skill-graft has one **Package**, `~/.apm/skill-graft/`, deployed into the home folder. A team that wants every
member to get the same grafted skills in one repository has no way to keep a **Package** there. APM 0.33.0
supports this at project scope: a local package registered in the project's `apm.yml` deploys into the project's
harness folders. The rest of skill-graft is done, so this is the next gap.

## What Changes

- **Project scope**: a **Package** at `<project>/.apm/skill-graft/`, laid out exactly like the user scope's,
  registered in `<project>/apm.yml` and deployed into `<project>/.claude/skills/` and the other harness folders.
  The project's own `.apm/` and `apm.yml` stay the user's; skill-graft owns only its subfolder.
- **Picking the Package**: every command except `init` acts on the nearest `.apm/skill-graft/` among the working
  folder and its ancestors, up to the home folder; if there is none, it acts on the user scope's (ADR 0004).
- **`init --project`** creates the **Package** in the working folder and registers it with
  `apm install ./.apm/skill-graft`, run there. Plain `init` is unchanged: user scope stays the default. Refused in
  the home folder, which is user scope.
- **`build`** in project scope runs `apm install ./.apm/skill-graft` from the project root and checks the
  project's `apm.yml`. APM's own errors, such as no harness detected, reach the user unchanged.
- **Package line**: `init`, `resolve`, `build`, `update`, `add`, `remove` and `rename` print
  `skill-graft: package: <path>` on stderr first, in either scope. **BREAKING** for anything parsing stderr;
  there are no users yet.
- **Overlap checks**: in project scope, a **Source** touching either scope's **Package** is an error, and the
  deploy-folder warnings cover both scopes' harness folders. Discovery skips every `.apm/skill-graft` folder, so
  a committed project **Package**'s vendored copies are never read as **Skills**.
- **Portable lock**: `upstream` is recorded relative to its **Source** (both scopes); in project scope a path
  **Source** inside the project is recorded relative to the **Package**. Teammates' builds of a committed
  **Package** then write the same lock.
- **Failed `init --project`** removes the folder it created, so no unregistered **Package** is left to be found.
- README: committing the whole **Package**, vendored skills included, so teammates need only APM.

Out of scope: a flag forcing user scope from inside a project (`cd ~` does that); picking APM targets; writing
either `apm.yml`.

## Capabilities

### New Capabilities

- `scope`: which **Package** a command acts on, and naming it on commands that write.

### Modified Capabilities

- `init`: `--project`, scope-dependent registration and retry hint, refusal in the home folder.
- `build`: APM command and manifest depend on the scope.
- `config`: overlap checks against both scopes' **Packages** and deploy folders.
- `resolve`: lock paths (`upstream` relative to its **Source**; project path **Sources** relative to the
  **Package**).
- `skill-discovery`: skip every `.apm/skill-graft` folder.
- `explain`: `why` names the skill's absolute upstream folder, the base for a new **Patch**, since the lock no
  longer does.

## Impact

- `paths.py` (root discovery; package, manifest and deploy folders per scope), `apm.py` (command, working folder,
  relative manifest entries), `init.py`, `cli.py` (flag, package line, help text), `config.py` (overlap, missing
  config hint), `discovery.py`, `lock.py`.
- Tests: `conftest.py` changes into the test's home folder, so the walk up never reaches the real home; the fake `apm`
  handles a project-scope install; a real-APM integration test for project scope.
- Docs: `README.md`, `docs/design.md` (measured project-scope APM behavior), ADR 0003 note and ADR 0004 (written).
- No new dependencies.

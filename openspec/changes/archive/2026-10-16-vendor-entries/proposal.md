# Proposal

## Why

Nothing is built yet. A walking skeleton (TOML in, skills deployed through APM out) proves the packaging, the CLI, and
the APM handoff end to end before the later changes (git-sources, resolve-hull, renames, patches, explain-and-edit) add
resolution on top.

## What Changes

- Packaging: `[project]` table in `pyproject.toml`, built with `uv`, console script `skill-graft`. Runtime dependencies:
  none yet (`tomlkit` arrives with the first command that edits the TOML).
- `skill-graft init`: creates `~/.apm/skill-graft/` with a commented `skill-graft.toml` and the two-line `apm.yml`, then
  registers it with `apm install -g <absolute path of ~/.apm/skill-graft>`. Refuses if the folder exists.
- Config: `skill-graft.toml` with `[sources.<alias>]` tables holding `path` only, and `entries`. Any other key
  (including `git`, `rename`, `bind`, `patches`, `reserved`) is an error, so no declared intent is silently ignored.
  Wrong value types, repeated entries, and sources overlapping the package are errors too.
- Skill discovery: every folder holding a `SKILL.md`, at any depth of a **Source**, symlinked folders included. **Skill
  ID** is `<alias>/<name>`, name from front matter `name:`, else the folder name; aliases and names are single path
  segments.
- `skill-graft build`: copies each **Entry**'s whole folder to `~/.apm/skill-graft/.apm/skills/<name>/`, swapping the
  folder in only once every copy succeeded, runs the same `apm install -g <absolute path>` as `init` (re-registering if
  needed), and fails unless APM exits 0 and `~/.apm/apm.yml` lists the package. `--no-install` stops before APM.

Out of scope: git sources, **References** and the **Hull**, the lock, **Renames**, **Binds**, **Patches**, **Reserved
names**, `resolve`/`add`/`update`/`why`/`tree`.

## Capabilities

### New Capabilities

- `init`: creating and registering the skill-graft APM package.
- `config`: reading `skill-graft.toml` (path **Sources**, **Entries**) and rejecting what it does not support.
- `skill-discovery`: finding **Skills** in a **Source** and deriving their **Skill IDs**.
- `build`: vendoring **Entries** into the package and deploying it through APM.

### Modified Capabilities

None.

## Impact

- New: `pyproject.toml` `[project]`, `src/skill_graft/`, `tests/`, `uv.lock`.
- Writes only under `~/.apm/skill-graft/`; `~/.apm/apm.yml` is written by APM, never by skill-graft (ADR 0003).
- Dev dependencies: `pytest`, `apm-cli==0.33.0` (for the APM integration tests).
- `README.md` status line and `docs/design.md` "Measured APM behavior" gain what this change verified.

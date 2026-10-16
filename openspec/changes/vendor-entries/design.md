# Design

## Context

Greenfield: only tooling config exists (`pyproject.toml` has tool tables, no `[project]`; `requirements-dev.txt`
holds `pre-commit`). Constraints from `AGENTS.md`: Python 3.11+, runtime stdlib (+ `tomlkit` later), `git` and
`apm` as subprocesses, `mypy --strict`, tests never touch the real home.

Verified before proposing, APM 0.33.0 via `uvx --from apm-cli==0.33.0`, `HOME` a scratch dir:

- `apm install -g <abs>/.apm/skill-graft` creates `~/.apm/apm.yml` if missing and appends the package as an
  **absolute path** under `dependencies.apm`. Re-running it is idempotent ("updated ref in apm.yml").
- A package of just the two-line `apm.yml` (no skills yet) registers and exits 0.
- Plain `apm install -g` afterwards redeploys from `~/.apm/apm.yml`, exit 0.
- Without `-t` and no `targets:` in `~/.apm/apm.yml`, skills go to `~/.agents/skills/`; with `-t claude`, to
  `~/.claude/skills/`.

## Goals / Non-Goals

**Goals:** a module layout the later changes extend without reshuffling; every failure is one clear message
and a non-zero exit.

**Non-Goals:** choosing APM targets for the user; any YAML parsing beyond the check below; Windows paths.

## Decisions

- **Layout**: `src/skill_graft/` with `cli.py` (argparse, subcommands `init`, `build`), `config.py`,
  `discovery.py`, `vendor.py`, `apm.py`, `paths.py` (home-derived paths via `Path.home()`, which honors
  `HOME`). One `SkillGraftError`; `cli.main` prints it to stderr and exits 1. argparse over click: stdlib only.

- **Packaging**: `uv_build` backend, `[project.scripts] skill-graft = "skill_graft.cli:main"`. Dev tools move
  to `[dependency-groups] dev` (`pytest`, `pre-commit`, `apm-cli==0.33.0`); `requirements-dev.txt` goes,
  `docs/development.md` switches to `uv sync` / `uv run`. `tomlkit` is not added until a command edits TOML.

- **No `-t` passed to APM**: targets are the user's APM config (`targets:` in `~/.apm/apm.yml`), not
  skill-graft's.

- **Registration check without YAML**: scan `~/.apm/apm.yml` lines for a list item (`- x`, quotes stripped)
  equal to `~/.apm/skill-graft` or its absolute path. Alternative, a YAML parser: not an allowed dependency
  (ADR 0003). Alternative, `apm deps list`: output format is not an API.

- **Front matter without YAML**: if `SKILL.md` starts with a `---` line, read lines up to the next `---`; the
  first top-level `name:` line gives the name, quotes stripped. Enough for `name:`; nothing else is read yet.

- **Discovery**: `os.walk` without following symlinks, pruning `.git` and stopping at any folder holding
  `SKILL.md`. Index is built per source as name → list of folders, so duplicates surface only when an entry
  names them (a third-party repo with a duplicate it never uses must not block the user).

- **Vendoring**: validate config, discovery and name clashes first; only then delete
  `~/.apm/skill-graft/.apm/skills/` and `copytree` each entry into it (ignoring `.git`). skill-graft owns
  that folder, so a full rewrite is the simplest way to drop stale skills; APM prunes the deployed copies.

- **Init template** (`skill-graft.toml`), comments only:

  ```toml
  # skill-graft.toml: the skills you want and where they come from.
  #
  # entries = ["own/chisel"]   # Skill IDs: <source alias>/<skill name>
  #
  # [sources.own]
  # path = "~/skills"          # a folder; skills are found at any depth
  ```

- **Tests**: pytest, `HOME` monkeypatched to `tmp_path`, fixture skills written in the test. A fake `apm`
  (a small script put first on `PATH`) records its argv, exits with a chosen code, and optionally writes
  `~/.apm/apm.yml`; it covers every failure path. One integration test runs the real `apm` from the dev group
  through `init` and `build`, skipped when `apm` is not on `PATH`.

- **Hooks**: a local `pytest` pre-commit hook (`uv run pytest`); the mypy hook gets `pytest` as an additional
  dependency so strict mode can type the tests.

## Risks / Trade-offs

- \[APM changes how it writes the dependency (e.g. `~` or a `path:` mapping)\] → the check accepts both `~` and
  absolute forms; the integration test pins 0.33.0 and catches a change on upgrade.
- [Line-scan check is fooled by the path appearing in a comment or another key] → acceptable; worst case a
  missed "not registered" error, never a false failure.
- [Symlinks inside a skill pointing outside it get dereferenced and vendored] → rare; revisit with git sources.
- \[`init` fails after creating the folder; re-running `init` then refuses\] → the error prints the
  `apm install -g` retry command.

## Migration Plan

None: nothing deployed yet.

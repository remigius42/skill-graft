# Design

## Context

Greenfield: only tooling config exists (`pyproject.toml` has tool tables, no `[project]`; `requirements-dev.txt` holds
`pre-commit`). Constraints from `AGENTS.md`: Python 3.11+, runtime stdlib (+ `tomlkit` later), `git` and `apm` as
subprocesses, `mypy --strict`, tests never touch the real home.

Verified before proposing, APM 0.33.0 via `uvx --from apm-cli==0.33.0`, `HOME` a scratch dir:

- `apm install -g <abs>/.apm/skill-graft` creates `~/.apm/apm.yml` if missing and appends the package as an **absolute
  path** under `dependencies.apm`. Re-running it is idempotent ("updated ref in apm.yml") and redeploys.
- A package of just the two-line `apm.yml` (no skills yet) registers and exits 0.
- Without `-t` and no `targets:` in `~/.apm/apm.yml`, skills go to `~/.agents/skills/`; with `-t claude`, to
  `~/.claude/skills/`.

## Goals / Non-Goals

**Goals:** a module layout the later changes extend without reshuffling; every failure is one clear message and a
non-zero exit, never a traceback.

**Non-Goals:** choosing APM targets for the user; any YAML parsing beyond the check below; Windows paths.

## Decisions

- **Layout**: `src/skill_graft/` with `cli.py` (argparse, subcommands `init`, `build`), `config.py`, `discovery.py`,
  `vendor.py`, `apm.py`, `paths.py` (home-derived paths via `Path.home()`, which honors `HOME`). One `SkillGraftError`;
  `cli.main` prints it to stderr and exits 1. argparse over click: stdlib only.

- **Packaging**: `uv_build` backend, `[project.scripts] skill-graft = "skill_graft.cli:main"`. Dev tools move to
  `[dependency-groups] dev` (`pytest`, `pre-commit`, `apm-cli==0.33.0`); `requirements-dev.txt` goes,
  `docs/development.md` switches to `uv sync` / `uv run`. `tomlkit` is not added until a command edits TOML.

- **Ownership**: skill-graft owns the package source, `~/.apm/skill-graft/.apm/skills/`; APM owns the deployed copies
  (`~/.agents/skills/`, `~/.claude/skills/`, …) and prunes the ones whose source is gone.

- **One APM call for `init` and `build`**: both run `apm install -g <absolute path of ~/.apm/skill-graft>`, never `~`
  (subprocess does not expand it) and never plain `apm install -g`. Repeating it is idempotent, so `build` re-registers
  a package the user removed from `~/.apm/apm.yml` instead of failing; the registration check then only guards APM's
  exit-code quirks (`docs/design.md`, "Measured APM behavior").

- **No `-t` passed to APM**: targets are the user's APM config (`targets:` in `~/.apm/apm.yml`), not skill-graft's.

- **Registration check without YAML**: scan `~/.apm/apm.yml` lines for a list item, either `- x` or `- path: x`, quotes
  and trailing `/` stripped, `~` expanded; it matches when `Path(x).resolve()` equals `~/.apm/skill-graft` resolved, so
  symlinked homes (macOS `/var` → `/private/var`) still match. Alternative, a YAML parser: not an allowed dependency
  (ADR 0003). Alternative, `apm deps list`: output is not an API.

- **Front matter without YAML**: a leading UTF-8 BOM is dropped; a first line of `---` (trailing whitespace allowed)
  opens front matter, closed by the next such line. The first unindented `name:` line gives the name: a comment
  (whitespace then `#`) is cut, then whitespace and matching quotes stripped. A value starting `>`, `|`, `&`, `*`, `[`
  or `{` is an error naming the file, never a silent fallback to the folder name.

- **Names and aliases**: a skill name or source alias must match `[A-Za-z0-9][A-Za-z0-9._-]*` and not be `.` or `..`, so
  it is one path segment and `<alias>/<name>` splits unambiguously. A bad alias fails config loading; a bad skill name
  fails only when an entry names it, like duplicates.

- **Discovery**: `os.walk(followlinks=True)`, pruning `.git` and any folder whose resolved path was already visited
  (symlink cycles), and stopping at any folder holding `SKILL.md`. Index is built per source as name → list of folders,
  so duplicates surface only when an entry names them (a third-party repo with a duplicate it never uses must not block
  the user).

- **Source overlap**: a source whose resolved path is inside `~/.apm/skill-graft/`, or contains it, is an error. One
  inside or containing a deploy folder (`~/.agents/skills`, `~/.claude/skills`, …) is a warning: what APM's pruning does
  there is unverified.

- **Vendoring**: validate config, discovery and name clashes first. Then `copytree` each entry (ignoring `.git`;
  symlinks, already checked to lead to files inside the skill, copied as files) into a fresh sibling
  `~/.apm/skill-graft/.apm/skills.new/`, and only when every copy succeeded swap it in: rename the old folder aside,
  rename the new one into place, delete the old. A failed copy deletes `skills.new/` and leaves `skills/` as it was.
  Every build first undoes a crashed run: if `skills/` is missing, `skills.old/` is the previous build and is renamed
  back; then any stale `skills.new/` or `skills.old/` is deleted.

- **Config value types**: `sources` must be a table of tables, each with a string `path`; `entries` a list of strings. A
  wrong type or an empty source table is an error naming the key; a repeated entry is an error naming it, not a
  deployed-name clash with itself.

- **Init template** (`skill-graft.toml`), comments only:

  ```toml
  # skill-graft.toml: the skills you want and where they come from.
  #
  # entries = ["own/chisel"]   # Skill IDs: <source alias>/<skill name>
  #
  # [sources.own]
  # path = "~/skills"          # a folder; skills are found at any depth
  ```

- **Tests**: pytest, `HOME` monkeypatched to `tmp_path`, fixture skills written in the test. A fake `apm` (a small
  script put first on `PATH`) records its argv, exits with a chosen code, and optionally writes `~/.apm/apm.yml`; it
  covers every failure path. One integration test runs the real `apm` from the dev group through `init` and `build`,
  skipped when `apm` is not on `PATH`.

- **Hooks**: a local `pytest` pre-commit hook (`uv run pytest`). The mypy hook runs in its own environment without the
  package installed, so `pyproject.toml` sets `mypy_path = "src"` and the hook gets `pytest` as an additional dependency
  so strict mode can type the tests.

## Risks / Trade-offs

- \[APM changes how it writes the dependency (e.g. `~` or a `path:` mapping)\] → the check accepts `~`, absolute and
  `path:` forms, compared resolved; the integration test pins 0.33.0 and catches a change on upgrade.
- [Line-scan check is fooled by the path appearing in a comment or another key] → acceptable: worst case a missed "not
  registered" error. A false failure needs APM to write a form the check does not know, which the integration test would
  catch.
- [A skill uses a symlink to share files from outside its folder] → an error naming the link, since a skill is its whole
  folder. Links to files inside are copied as files; links to any folder are an error too, since two folder links can
  form a cycle a check would have to chase.
- [Front matter parsing is a subset of YAML] → unsupported forms fail loudly naming the file.
- \[`init` fails after creating the folder; re-running `init` then refuses\] → the error prints the `apm install -g`
  retry command; `build` also re-registers.

## Migration Plan

None: nothing deployed yet.

# Proposal

## Why

`pipeline` and `infra` still read the **Scope** from a module global that `commands/scope.of` sets with `paths.use`: a
dependency the import-linter contracts cannot see and no signature shows. ADR 0008 removes it in two changes;
`commands-own-orchestration` made `commands` build the `Scope` and take it as a parameter. This is the second and last:
the `Scope` goes down into every function that reads it, and the global goes.

## What Changes

- Every `pipeline` and `infra` function that reads the global today takes the `Scope` as an explicit parameter:
  - `config`: `load`, `text`, `parse` (and through it the source checks against the packages and deploy folders).
  - `lock`: `render` (a source's relative path in project scope); `write` and `read` take their file, no default.
  - `discovery`: `index` (skips the **Package** it would read its own output from).
  - `vendor`: `vendor` takes its skills folder, no default.
  - `compute`: `compute_hull` and `known`, which pass it to `discovery` and `config`.
  - `apm`: `install`, `registered`, `command_line`.
  - `commands` that read `paths.*` themselves (`init`, `edit.read`/`write`, `update`) use the `Scope` they hold; `init`
    gains a `Scope` parameter.
- `infra/paths.py`: `Scope` gains the paths the module functions derive today (`config_file`, `manifest`,
  `deploy_folders`, `packages`). `use`, `_in_use`, `in_use` and the functions reading them (`root`, `scope`, `package`,
  `config_file`, `skills`, `deploy_folders`, `packages`, `manifest`) are deleted. The pure helpers stay: `discover`,
  `in_package`, `folded`, `overlap`, `cache`.
- `commands/scope.of` loses `paths.use` and its reset: it builds the `Scope` and prints the `package:` notice. Nothing
  holds the **Scope** globally.
- The git `Cache`: `compute_hull` and `known` take it as a required parameter. Each command that reads git **Sources**
  builds one `Cache` and passes it down: `tree`, `why`, `resolve`, `build`, the edits, `update` (already does).
  `tree --format mermaid` uses the one it resolved with, not a second. No `Cache(paths.cache())` below `commands`.
- `_explain` loads the config through `resolve.load` instead of its own copy; `show` moves from `resolve` to `explain`,
  its natural home.
- Tests below `cli` build a `Scope` on a temporary folder: a `scope` fixture, `Scope(home)`, in `tests/conftest.py`.
  `HOME` and `XDG_*` stay redirected.

No user-visible change: every output, file and exit code stays byte for byte. No CHANGELOG entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: a refactor (`skip_specs: true`).

## Impact

- `src/skill_graft/infra/paths.py`, `infra/apm.py`.
- `src/skill_graft/pipeline/config.py`, `lock.py`, `discovery.py`, `vendor.py`, `compute.py`.
- `src/skill_graft/commands/scope.py`, `init_package.py`, `edit.py`, `update.py`, `resolve.py`, `build.py`,
  `explain.py`; `cli.py`: `scope.of` called as a function, `init` passed the `Scope`.
- Tests: `tests/pipeline/` and `tests/infra/` pass a `Scope` and a `Cache`; the tests of `paths.in_use` and of
  `scope.of` resetting the global go; patches of `lock.write`, `lock.render`, `vendor.vendor`, `config.load` take the
  new signatures.
- `docs/design.md` where it names the global, if it does; `CONTEXT.md` unchanged.

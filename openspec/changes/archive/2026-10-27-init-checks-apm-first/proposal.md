# Proposal

## Why

Without APM installed, `skill-graft init` creates `~/.apm/skill-graft/`, then fails on the missing `apm` and says to
retry with `apm install -g <package>`. A user who installs APM and runs `skill-graft init` again, the obvious retry,
gets `<package> already exists; init does nothing`, which names no way forward. `init` writes the **Package** before it
knows it can register it, and its refusal of an existing folder does not tell a registered **Package** from one APM
never listed.

## What Changes

- `init` and `init --project` check that `apm` is on `PATH` before creating anything. Without it they exit non-zero,
  create nothing, and say to install APM and run the same `init` again.
- When the folder exists but the scope's `apm.yml` does not list it, the refusal says how to register it: at user scope
  `apm install -g <absolute path of the package>`, at project scope `apm install ./.apm/skill-graft` run in the project
  root, shell-quoted, if the folder holds its own `apm.yml`. A listed **Package** gets the refusal as today. The
  existing-folder refusal comes before the `apm` check.
- `init` still never modifies an existing folder and never runs `apm` for one; it does not become idempotent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `init`: the registration requirement checks for `apm` before creating the folder, and a missing `apm` no longer leaves
  a folder behind; the existing-folder requirement says how to register an unlisted **Package**.

## Impact

- `src/skill_graft/infra/apm.py`: a check that `apm` is on `PATH`, sharing the missing-APM message with `install`; the
  APM command as one shell-quoted line.
- `src/skill_graft/commands/init_package.py`: the check before `mkdir`; the hint in the existing-folder refusal.
- `tests/commands/test_init_package.py`; `docs/design.md`'s `init` entry.
- `CHANGELOG.md` at archive: a `### Fixed` entry.

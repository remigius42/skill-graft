# Design

## Context

`init_package.init` resolves the **Package** path, prints it, `mkdir`s it (`FileExistsError` is the existing-folder
refusal), writes the two files, then calls `apm.install()`, which learns `apm` is missing only when `subprocess.run`
raises `FileNotFoundError`. At user scope a failure keeps the folder; at project scope an unlisted one is removed.
`_listed()` already asks `apm.registered()` whether the scope's `apm.yml` lists the package, treating an unreadable one
as not listed. The user-scope retry hint spells out `apm install -g <path>` by hand, unquoted, beside `apm._command()`,
which builds the same command. See proposal.md for why.

## Goals / Non-Goals

**Non-Goals:**

- Making `init` register an existing folder. That needs `init` to run `apm` against a folder it did not make, and the
  spec promises it never does.
- Checking APM's version. The README pins 0.33.0; a version check is a separate question.
- `build`, which also writes `.apm/skills/` and the lock before learning `apm` is missing. A separate change.

## Decisions

- **Order: existing folder, then `apm`, then `mkdir`.** The existing-folder refusal stays first, so a folder left by an
  older skill-graft still gets its hint even without APM; the hint's `apm install` then fails with the shell's own
  "command not found", which says what to do. Checking `apm` first would tell the user to rerun `init`, which then
  refuses: the dead end this change removes. The spec pins the order with a scenario. Checking `apm` before `mkdir`
  means nothing is written without it.
- **Existing means `exists() or is_symlink()`**, so a dangling symlink, which `mkdir` refuses, is refused before the
  `apm` check too. A `FileExistsError` from `mkdir` (a race) goes through the same refusal, hint included.
- **`shutil.which("apm")`, not a trial `apm --version`.** It answers the one question asked and runs nothing. A broken
  `apm` still fails in `install()`, which keeps its `FileNotFoundError` handling for the gap between check and run.
- **The check lives in `infra/apm.py`** (`apm.require()`), next to `install()`, sharing one `MISSING` message, so the
  two cannot drift. `init` adds the retry line: `install APM, then run: skill-graft init` (`--project` when given), the
  same `then run:` shape as its other hints.
- **One command line, built once.** `apm.command_line()` returns `shlex.join(_command())`; the user-scope retry hint and
  the new register hint both use it, so neither spells the command by hand and a path with a space pastes into a shell
  intact. At project scope the hint adds the folder to run it in: `run in <root>: <command line>`.
- **The register hint reuses `_listed()`** (the scope's `apm.yml`, no `apm` run), and is given only when the folder
  holds its own `apm.yml`: without one APM cannot install it, and the refusal stays bare. Listed: the message stays
  `… already exists; init does nothing`.

## Risks / Trade-offs

- `apm` on `PATH` but not runnable → `install()` still fails as today, with the user-scope retry hint.
- A relative `PATH` entry: `which` resolves it from the working folder, `install()` runs `apm` from the scope's root, so
  the two can disagree → rare; if `which` finds it and the run does not, `install()` fails as before.
- `_listed()` reads an undecodable `apm.yml` as not listing the package, so the hint may name a registered one → it only
  names a command, and running it re-registers harmlessly.
- The hint can suggest registering a folder the user made by hand → it only names a command; nothing runs.

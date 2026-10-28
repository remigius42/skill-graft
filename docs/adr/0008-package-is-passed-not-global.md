# The package is passed explicitly, never held in a global

Every command acts on one **Package** (ADR 0004), and every module that reads or writes its files takes it as an
explicit `Package` parameter: a frozen dataclass in `infra/paths.py` holding only its scope's root (the home
folder or a project folder), deriving from it the **Package**'s own folder, `.apm/skill-graft` inside the root,
its scope (user when the root is the home folder) and every other path, the user scope's package and deploy
folders included. `paths.use` and its module globals go: the import-linter contracts see only imports, so a
global read three layers down was a dependency no check could see, and an explicit parameter shows it in every
signature, where mypy checks it. The home folder still comes from `HOME`, as the environment gives it; that is
input, not state skill-graft keeps. `commands` builds the `Package` from the working folder `cli` hands it:
`init` takes the home folder, `init --project` the working folder, every other command the one `discover` finds.
A `Package` may name a folder `init` has yet to create. The git cache is not part of it: it lives under
`XDG_CACHE_HOME`, or `~/.cache` when that is unset or relative, shared by every package, so each command builds
the `Cache` it needs once and passes it down too.

## Considered Options

- A `contextvars` value: fewer signatures change, but the dependency stays as hidden as the global.
- A field on `Config`: most pipeline functions already take one, but it mixes what `skill-graft.toml` says with
  where it lives, and `init`, `discover` and the APM calls have no `Config`.
- Naming the type `APMPackage`, against Python's packages: code and `CONTEXT.md` would disagree; the docstring
  says it is the APM package, and it only ever appears as a value.

## Consequences

Tests below `cli` build a `Package` on a temporary folder; `HOME` and `XDG_*` stay redirected, for APM, the
cache and the user scope's folders. The migration takes two changes. The first moves `resolve`, `build`, `tree`
and `why` into `commands`, which take a `Package` from the start; `cli` gets the `Package` for every command
from the one function in `commands` that builds it, which keeps the global in step with `paths.use(package.root)`
in place of `cli`'s own `discover`. The second passes the `Package` down into `pipeline` and `infra` and deletes
that call with the global.

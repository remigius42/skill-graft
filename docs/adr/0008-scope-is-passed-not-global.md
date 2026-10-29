# The scope is passed explicitly, never held in a global

Every command acts on one **Package** in one **Scope** (ADR 0004), and every module that reads or writes the
**Package**'s files or the **Scope**'s deploy folders takes it as an explicit `Scope` parameter: a frozen dataclass in
`infra/paths.py` holding only the **Scope**'s root (the home folder or a project folder), deriving from it the
**Package** (`scope.package`, `.apm/skill-graft` inside the root), whether it is user scope (when the root is the home
folder) and every other path, the user scope's package and deploy folders included. `paths.use` and its module globals
go: the import-linter contracts see only imports, so a global read three layers down was a dependency no check could
see, and an explicit parameter shows it in every signature, where mypy checks it. The home folder still comes from
`HOME`, as the environment gives it; that is input, not state skill-graft keeps. `commands` builds the `Scope`, reading
the working folder itself and only when it needs it, so plain `init` works in a deleted one: `init` takes the home
folder, `init --project` the working folder, every other command the one `discover` finds. A `Scope` may name a
**Package** `init` has yet to create. The git cache is not part of it: it lives under `XDG_CACHE_HOME`, or `~/.cache`
when that is unset or relative, shared by every package, so each command builds the `Cache` it needs once and passes it
down too.

## Considered Options

- A `contextvars` value: fewer signatures change, but the dependency stays as hidden as the global.
- A field on `Config`: most pipeline functions already take one, but it mixes what `skill-graft.toml` says with where it
  lives, and `init`, `discover` and the APM calls have no `Config`.
- Naming the type `Package`: commands act on a **Package**, but `CONTEXT.md`'s **Package** is the `.apm/skill-graft`
  folder, which the type derives from the root it holds; `package.root` would read as the package's own folder, and the
  deploy folders are no part of a **Package**.
- Holding the **Package**'s folder instead of the root: the type would match the term, but every other path derives from
  the root, so each would climb back up from the folder.

## Consequences

Tests below `cli` build a `Scope` on a temporary folder; `HOME` and `XDG_*` stay redirected, for APM, the cache and the
user scope's folders. The migration takes two changes. The first moves `resolve`, `build`, `tree` and `why` into
`commands`, which take a `Scope` from the start; `cli` gets the `Scope` for every command from the one function in
`commands` that builds it, which keeps the global in step with `paths.use(scope.root)` in place of `cli`'s own
`discover`. The second passes the `Scope` down into `pipeline` and `infra` and deletes that call with the global.

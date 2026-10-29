# skill-graft drives APM but never edits its manifest

`build` runs `apm install -g <absolute path of ~/.apm/skill-graft>` itself and checks the exit code and that
`~/.apm/apm.yml` lists `~/.apm/skill-graft`, because APM 0.33.0 fails a wrong `path:` with exit code 1 while printing
"No changes", and a user running it by hand misses that. skill-graft never writes `~/.apm/apm.yml`: it is the user's
file, shared with other packages, and the runtime dependencies (standard library and `tomlkit`) include no YAML writer.
`init` and `build` register the package through that `apm install -g` instead.

In project scope (ADR 0004) the same holds for the project's `apm.yml`: skill-graft runs
`apm install ./.apm/skill-graft` from the project root, where APM 0.33.0 accepts and records the relative path, and
checks that `apm.yml` there lists it.

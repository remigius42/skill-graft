# skill-graft drives APM but never edits its manifest

`build` runs `apm install -g` itself and checks the exit code and that `~/.apm/apm.yml` lists
`~/.apm/skill-graft`, because APM 0.33.0 fails a wrong `path:` with exit code 1 while printing "No changes", and
a user running it by hand misses that. skill-graft never writes `~/.apm/apm.yml`: it is the user's file, shared
with other packages, and the runtime dependencies (standard library and `tomlkit`) include no YAML writer.
`init` registers the package through `apm install -g ~/.apm/skill-graft` instead.

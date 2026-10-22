# graft-check eval

`run.sh` runs the working copy of `skills/graft-check/` headless with `claude -p` and checks its reports. An agent's
report varies between runs and costs tokens, so this is an eval, run by hand when the skill changes, outside
pre-commit and CI.

```sh
uv sync
CLAUDE_CODE_OAUTH_TOKEN=<token> evals/graft-check/run.sh             # every scenario
CLAUDE_CODE_OAUTH_TOKEN=<token> evals/graft-check/run.sh clean fix   # only these
```

`ANTHROPIC_API_KEY=<key>` works as well. `claude setup-token` prints a token billed to your subscription. Without a
token or a key the script stops before building anything. Each scenario is one `claude` session (`fix` takes two
turns), so a full run costs about nine times one.

## Scenarios

Each builds its own project package in the temporary folder, the skill in the project's `.claude/skills/`, over a git
source `up` committed with `GIT_AUTHOR_*` and `GIT_COMMITTER_*` set.

| Scenario           | Package                                                        | Checks                                                                       |
| ------------------ | -------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `defects`          | the defects package, built                                     | each defect named with its kind; the patched line not a rewrite; unchanged   |
| `clean`            | `up/lead` calling `/code-style`, no defect, built              | it found nothing; no advice to build; unchanged                              |
| `never-built`      | the clean package, not built                                   | advice to run `skill-graft build`; unchanged                                 |
| `scoped`           | the defects package, `/graft-check up/code-style`              | its `GET /status` named as false; none of `lead`'s defects; unchanged        |
| `unknown-argument` | the defects package, `/graft-check up-lead`, the deployed name | it names `up-lead` and lists `up/lead`; none of `lead`'s defects; unchanged  |
| `build-fails`      | an entry `up/missing` the source lacks                         | the build's error shown; unchanged                                           |
| `newer-lock`       | the clean package; the throwaway lock says `version = 2`       | advice to update and start a new session; unchanged                          |
| `fix`              | the defects package; a second turn accepts one fix             | `up/review` left the hull; advice to build; that bind the only config change |

The defects package: `up`, prefixed `up-`, whose entry `up/lead` holds one defect of each kind but one (a call written
in words, "run the notes skill"; a false reference, `` `GET /review` ``; a prose word the prefix rewrites, "follow-up
question"; a relative link into a renamed skill's folder), plus a user patch adding a line to `lead`, and a path source
`art` whose `format` is not what `lead` means by `/format`: the wrong target. `up/code-style` holds a false
`` `GET /status` `` for `scoped`. `newer-lock` rewrites the version in the `skill-graft` wrapper the script puts on
`PATH`, since skill-graft itself only writes version 1.

`HOME`, `XDG_CACHE_HOME` and `TMPDIR` point into the temporary folder, so the real `~/.claude`, `~/.apm` and
`~/.cache/skill-graft` are never read or written, and no personal setting, hook or deployed skill changes the run.
`--allowedTools` grants `skill-graft`, `mktemp`, `diff`, reads, searches and subagents; headless, any other tool call is
denied. `--add-dir` grants the whole temporary folder, where the throwaway builds, the cache and the sources lie,
outside the project.

The script prints each report, then one `ok` or `FAILED` line per check, and exits non-zero when any check fails or
`claude` does. A finding counts when one line of the report holds its text and its kind. Read the reports too: the
grep only shows that each finding is named.

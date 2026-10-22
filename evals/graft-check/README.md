# graft-check eval

`run.sh` runs the working copy of `skills/graft-check/` headless with `claude -p` and checks its report. An agent's
report varies between runs and costs tokens, so this is an eval, run by hand when the skill changes, outside
pre-commit and CI.

```sh
uv sync
CLAUDE_CODE_OAUTH_TOKEN=<token> evals/graft-check/run.sh   # or ANTHROPIC_API_KEY=<key>
```

`claude setup-token` prints a token billed to your subscription. Without a token or a key the script stops before
building anything.

It builds, in a new temporary folder:

- a git source `up`, prefixed `up-`, committed with `GIT_AUTHOR_*` and `GIT_COMMITTER_*` set, whose entry `up/lead`
  holds one defect of each kind but one: a call written in words ("run the notes skill"), a false reference
  (`` `GET /review` ``), a prose word the prefix rewrites ("follow-up question"), and a relative link into a renamed skill's
  folder;
- a path source `art` whose `format` is not what `lead` means by `/format`: the wrong target;
- a project package over both, built in place with `--no-install`, and the skill in the project's `.claude/skills/`.

`HOME`, `XDG_CACHE_HOME` and `TMPDIR` point into the temporary folder, so the real `~/.claude`, `~/.apm` and
`~/.cache/skill-graft` are never read or written, and no personal setting, hook or deployed skill changes the run.
`--allowedTools` grants `skill-graft`, `mktemp`, `diff`, reads, searches and subagents; headless, any other tool
call is denied.

The script prints the report, then one line per defect: `found` when a line of the report holds the defect's text and
its kind, `MISSING` otherwise. It exits non-zero when `claude` fails, a defect is missing, or the eval package's files
changed. Read the report too: the grep only shows that each finding is named.

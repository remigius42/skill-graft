# Tasks

## 1. Lock version

- [x] 1.1 Pin the lock's version 1 keys in `tests/test_lock.py` (a renamed, patched **Skill** from a git **Source** with
  a `subdirectory`, a plain **Entry** from a path **Source**, a bound edge, a suggestion), its failure message saying to
  raise `version`; verify it passes against today's lock writer and goes red when a key is added to the writer
  (reverted after)

## 2. The skill

- [x] 2.1 Add `skills/graft-check/SKILL.md` with front matter (`name: graft-check`, `disable-model-invocation: true`, a
  description saying it runs only when the user asks) and a body stub; add `tests/test_check.py` asserting the front
  matter, and that a git **Source** with `subdirectory = "skills"`, a temporary repository committing a copy of the
  working tree's `skills/`, with `entries = ["sg/graft-check"]` resolves to `sg/graft-check` alone with no warning and
  no suggestion; verify the tests pass
- [x] 2.2 Write the skill's body by the rules in `resources/writing-for-agents/writing-for-agents-skill.md` and, for a
  skill, `resources/writing-for-agents/writing-for-agents-skill-mechanics.md` (user-invoked branch), with one exception:
  the description keeps the "only when the user asks" wording, since harnesses other than Claude Code may ignore
  `disable-model-invocation`. The body covers:
  - `mktemp -d`, then build `--into` that folder, read the **Package** line, stop on a lock `version` other than 1 (a
    higher one with the advice to update the **Source** it was installed from, run `skill-graft build` there and start a
    new session, naming no alias)
  - inputs: the throwaway lock and vendored copies; **Upstream** folders from the lock for path **Sources** and one
    `skill-graft why` per git **Source**; a patched **Skill**'s `patches` read, their changed lines counted as intended;
    `skill-graft tree` for each edge's written name; optional **Skill ID** arguments
  - the five kinds with a placeholder example each; the per-skill subagent fan-out and its report shape
  - fixes one at a time after the user's yes: a **Bind** only when every use of the name in that **Source**'s
    **Upstream** text needs it, else a **Patch**; `add`/`bind`/`unbind`, or the README recipe with the **Package** path;
    rebuild `--into` a new `mktemp -d` folder after each and name **Skills** that left or joined the **Hull**; undo a
    failed **Patch**'s file and own list item only, the key and table only if it created them
  - close with the `skill-graft build` advice when a fix was accepted or the first throwaway `.apm/skills/` differs from
    the **Package**'s (`diff -rq`, a missing one counting as different); otherwise say the **Package** matches its
    config and that deployment is not checked
  - verify: a review of the finished `SKILL.md` against every rule of both resource files (context pointer, the
    two loads, information hierarchy and disclosure, completion criteria, splitting, leading words, negation,
    pruning, invocation) finds nothing left to fix, each rule named with how the text meets it; then
    `tests/test_check.py` still passes (no **Reference** crept in) and `pre-commit run --all-files` is green

## 3. Installing it

- [ ] 3.1 Add the commented `[sources.skill-graft]` block (with `subdirectory = "skills"`) and the `update`/`add`
  commands, with the note that every `build` fails until that `update`, to the `init` template; verify a test for the
  "Template shows graft-check" scenario passes, uncommenting the block and loading it
- [ ] 3.2 Document installing and running `graft-check` in `README.md`; verify the documented commands match the
  template and `pre-commit run --all-files` is green

## 4. Eval

- [ ] 4.1 Write `evals/graft-check/run.sh` and its README: a temporary project **Package** over a local git **Source**
  (committed with `GIT_AUTHOR_*` and `GIT_COMMITTER_*` set)
  with one planted defect per kind, the working copy in the project's `.claude/skills/`, `HOME`, `XDG_CACHE_HOME` and
  `TMPDIR` in the temporary folder, `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` required (neither: stop, naming
  `claude setup-token`), `claude -p` run there with `--allowedTools` for `Bash(skill-graft:*)`, `Bash(mktemp:*)`,
  `Bash(diff:*)`, reads, searches and subagents, and a grep per defect; verify a manual run reports all five, leaves the
  eval **Package**'s files unchanged, and leaves the real `~/.apm`, `~/.claude` and `~/.cache/skill-graft` unchanged

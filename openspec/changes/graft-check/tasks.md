# Tasks

## 1. Lock version

- [ ] 1.1 Pin the lock's version 1 keys in `tests/test_lock.py` (a renamed, patched **Skill**, a bound edge, a
  suggestion), its failure message saying to raise `version`; verify the test passes against today's lock
  writer

## 2. The skill

- [ ] 2.1 Add `skills/graft-check/SKILL.md` with front matter (`name: graft-check`,
  `disable-model-invocation: true`, a description saying it runs only when the user asks) and a body stub; add
  `tests/test_check.py` asserting the front matter, and that a temporary path **Source** holding the tracked
  files under `skills/` (`git ls-files skills`) with `entries = ["sg/graft-check"]` resolves to
  `sg/graft-check` alone with no warning and no suggestion; verify the tests pass
- [ ] 2.2 Write the skill's body with the mp-writing-for-agents skill:
  - build `--into` a new folder under the system's temporary folder, read the **Package** line, stop on a lock
    `version` other than 1 (a higher one with the update advice)
  - inputs: the throwaway lock and vendored copies, one `skill-graft why` per **Source** joined with the lock's
    `upstream`; optional **Skill ID** arguments
  - the five kinds with a placeholder example each; the per-skill subagent fan-out and its report shape
  - fixes one at a time after the user's yes: a **Bind** only when every use of the name in that **Source**'s
    **Upstream** text needs it, else a **Patch**; `add`/`bind`/`unbind`, or the README recipe with the **Package**
    path; rebuild `--into` a new folder after each and name **Skills** that left or joined the **Hull**; undo a
    failed **Patch**'s file and own list item only
  - close with the `skill-graft build` advice when a fix was accepted or the first throwaway lock differs from
    the **Package**'s; otherwise say the **Package** matches its config and that deployment is not checked
  - verify `tests/test_check.py` still passes (no **Reference** crept in) and `pre-commit run --all-files` is
    green

## 3. Installing it

- [ ] 3.1 Add the commented `[sources.skill-graft]` block (with `subdirectory = "skills"`) and the `update`/`add`
  commands to the `init` template; verify a test for the "Template shows graft-check" scenario passes,
  uncommenting the block and loading it
- [ ] 3.2 Document installing and running `graft-check` in `README.md`; verify the documented commands match the
  template and `pre-commit run --all-files` is green

## 4. Eval

- [ ] 4.1 Write `evals/graft-check/run.sh` and its README: a temporary project **Package** over a local git
  **Source** with one planted defect per kind, the working copy in the project's `.claude/skills/`, `HOME`,
  `XDG_CACHE_HOME` and `TMPDIR` in the temporary folder and `ANTHROPIC_API_KEY` required, `claude -p` run there
  with `--allowedTools` for `Bash(skill-graft:*)`, reads, searches and subagents, and a grep per defect; verify a
  manual run reports all five, leaves the eval **Package**'s files unchanged, and leaves the real `~/.apm`,
  `~/.claude` and `~/.cache/skill-graft` unchanged

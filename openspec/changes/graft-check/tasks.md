# Tasks

## 1. The skill

- [ ] 1.1 Add `skills/graft-check/SKILL.md` with front matter (`name: graft-check`,
  `disable-model-invocation: true`, a description saying it runs only when the user asks) and a body stub; add
  `tests/test_check.py` asserting the front matter and that a path **Source** of `skills/` with
  `entries = ["sg/graft-check"]` resolves to `sg/graft-check` alone with no warning; verify the tests pass
- [ ] 1.2 Write the skill's body with the mp-writing-for-agents skill: build with `--no-install` and read the
  **Package** line, the lock `version` check with its two messages, the inputs (lock, `skill-graft why`, vendored
  copy), optional **Skill ID** arguments, the five kinds with an example each, the per-skill subagent fan-out and
  report shape, fixes one at a time after the user's yes through `add`/`bind`/`unbind` or the README patch recipe
  with its undo, the rebuild after each, and the closing `skill-graft build` advice; verify `tests/test_check.py`
  still passes (no **Reference** crept in) and `pre-commit run --all-files` is green

## 2. Installing it

- [ ] 2.1 Add the commented `[sources.skill-graft]` block and the `update`/`add` commands to the `init` template;
  verify a test for the "Template shows graft-check" scenario passes, uncommenting the block and loading it
- [ ] 2.2 Document installing and running `graft-check` in `README.md`; verify the documented commands match the
  template and `pre-commit run --all-files` is green

## 3. Eval

- [ ] 3.1 Write `evals/graft-check/run.sh` and its README: a temporary project **Package** over a local git
  **Source** with one planted defect per kind, the skill copied into the project's `.claude/skills/`,
  `claude -p "/graft-check"` run there, and a grep per defect; verify a manual run reports all five and touches
  nothing under `~/.apm`

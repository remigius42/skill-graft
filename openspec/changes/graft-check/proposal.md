# Proposal

## Why

skill-graft finds **References** by their form alone, so a **Hull** can be quietly wrong: "run the grilling
skill" is missed, `/tmp` is taken for a call, a **Prefix** rewrites a word that was never a name, and a link
into another **Skill**'s folder breaks once it is renamed. An agent reading the text catches these; skill-graft
itself must not ask one (ADR 0006). A **Check** puts that agent in a skill the user runs, whose findings become
config the user accepts.

## What Changes

- A new skill, `skills/graft-check/SKILL.md` in this repository, installed like any other: the user declares the
  repository as a **Source** and `<alias>/graft-check` as an **Entry**. Invoked only by the user
  (`/graft-check [skill-id…]`), never by the model on its own.
- It builds with `skill-graft build --no-install`, then reads the lock, each **Hull** **Skill**'s **Upstream**
  folder and its vendored copy, and reports: missed **References**, false **References**, **References** resolved
  to the wrong **Skill**, rewrites that changed the wrong text or missed a name, and relative links vendoring
  broke. Stale **Patches** are out of scope.
- For each finding it proposes a fix (`skill-graft add`, `bind`, `unbind`, or a **Patch** written by the README's
  recipe), a **Bind** only where every **Reference** to that name from that **Source** needs it, and applies it
  only once the user accepts it, then rebuilds with `--no-install` and names **Skills** that left or joined the
  **Hull**. A failed **Patch** is undone without touching earlier ones. It never deploys: whenever the lock
  changed, it ends by telling the user to run `skill-graft build`.
- A lock `version` it does not know stops it, with the update that fixes it (the skill's **Source** or the CLI).
  The lock's version 1 keys are pinned by a test, so a layout change has to raise `version`.
- `skill-graft init` writes the lines that install it into its commented template; `README.md` explains them.
- An opt-in eval script plants one defect of each kind in a synthetic **Package** and runs the skill headless,
  outside pre-commit and CI.

## Capabilities

### New Capabilities

- `check`: the `graft-check` skill: how it is installed and invoked, what it reads, what it reports, and how
  fixes are applied.

### Modified Capabilities

- `init`: the template also shows, commented out, how to install `graft-check`.
- `resolve`: the lock's layout is tied to its `version`.

## Impact

- New `skills/graft-check/` and `evals/graft-check/`; `src/skill_graft/init.py` (template only).
- Tests in `tests/test_init.py`, `tests/test_lock.py` and a new `tests/test_check.py`.
- `README.md`; `.cspell.yaml` for new words. No change to resolution, the config format or the lock's content.

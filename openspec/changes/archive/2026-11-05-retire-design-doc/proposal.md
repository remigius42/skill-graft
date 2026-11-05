# Proposal

## Why

`docs/design.md` was the design written before the first OpenSpec change, meant to give way to the specs as they landed.
It never did: every change kept it in step, so it became a second prose spec beside `openspec/specs/`, and the README
grew task guides that crowd out its reference. A check of `design.md` against the specs found no contradiction, but six
behaviors a user sees that only `design.md` states; deleting it without them leaves them specified nowhere.

## What Changes

- `docs/design.md` is deleted. What the specs leave out, how and why it works, moves to `docs/architecture.md`; the
  measurements of APM 0.35.0 to `docs/apm-behavior.md`. The original design stays in git
  (`git show f10e879:docs/design.md`).
- The README's task guides (reviewing a **Source**, editing by hand, updating, writing a **Patch**, a project
  **Package**, graft-check) move to `docs/howto.md`; the README keeps the pitch, installation, a quickstart, the
  commands, the config, the cache and security.
- `docs/README.md` maps every doc; CONTEXT.md, CONTRIBUTING.md and AGENTS.md link to it, and ADR mentions become links.
- The README shows the skill-graft logo, floated right beside its title and pitch. `docs/assets/` holds it twice: the
  full mark for 64 px and up, and a small one for less, such as a favicon.
- The README links the docs, CONTEXT.md and the logo relatively, so on GitHub each ref's README leads to that ref's
  docs. The build rewrites those links to absolute ones naming the release, `blob/v<version>/`, so the README on PyPI
  leads to that release's guides; the build backend becomes hatchling, with hatch-fancy-pypi-readme.
- The six behaviors only `design.md` states become requirements and scenarios, each pinned by a test:
  - `deploy` compares the lock parsed: a comment or line endings an editor added are no difference.
  - The notice for a changed path **Source** **Skill** is
    `<skill id> changed in its path source since skill-graft.lock: deployed as is`.
  - The mermaid.live link's state holds `"mermaid": "{\"theme\": \"default\"}"`, its fragment unpadded.
  - `skill-graft.toml` is not scanned for **Hidden characters**.
  - A failing resolution lists failing **Patches** under `patches do not apply:`, then **Hidden characters** under
    `hidden characters:`, then the error that stopped the walk.
  - An edit's or `resolve`'s **Hull diff** reads the copies in the `.apm/skills.old/` a killed run left, as the next
    writing run would recover them.

No behavior changes: each requirement states what skill-graft already does.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deploy`: "Deploy what the lock records" compares the lock parsed; "Changed path Source deployed" gives the notice's
  text.
- `explain`: "Tree as a mermaid.live link" gives the state's `mermaid` field and the unpadded fragment.
- `hidden-characters`: "Hidden characters fail resolution" scans no `skill-graft.toml`; "One run reports every hidden
  character" gives the headers and their order.
- `edit`: "Edit reports the hull diff" reads a killed run's `.apm/skills.old/`.

## Impact

- Docs: `README.md`, `AGENTS.md`, `CONTEXT.md`, `CONTRIBUTING.md`, `docs/security.md`, two ADRs; new `docs/README.md`,
  `docs/howto.md`, `docs/architecture.md`, `docs/apm-behavior.md`, `docs/assets/skill-graft.svg` and
  `docs/assets/skill-graft-small.svg`; `docs/design.md` removed. `.markdownlint.yaml` allows `<img>`, which alone can
  size and float the logo.
- Tests for the behaviors no test pins yet: `tests/commands/test_deploy.py` (a reformatted lock),
  `tests/cli/test_hidden_characters.py` (the config not scanned), `tests/commands/test_review.py` (`resolve --dry-run`
  after a killed run) and `tests/pipeline/test_hull.py` (the error that stops the walk last). No change to `src/`: each
  passed as written.
- Build: `pyproject.toml`'s `[build-system]` moves from `uv_build` to hatchling and hatch-fancy-pypi-readme, its
  `readme` to the hook's substitutions; the wheel holds the same files as before, the sdist also hatchling's
  `.gitignore`. `tests/cli/test_pypi_readme.py` builds the wheel and checks its description's links.

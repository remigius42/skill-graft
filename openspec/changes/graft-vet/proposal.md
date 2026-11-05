# Proposal

## Why

`skill-graft vet` flags what patterns can see; an author writing to a **Skill**'s reader can phrase around every
pattern. A **Vet** also needs a reader that looks for intent, and a way to tell when that reader was steered, without
letting **Skill** text reach the agent that holds the user's shell (ADR 0007, ADR 0010). The `graft-vet` skill is that
half: one confined reader per **Skill**, merged with the scan in code, reporting only.

## What Changes

- A new skill, `skills/graft-vet/`, installed as `graft-check` is, `disable-model-invocation: true`:
  `/graft-vet [skill-id…]`, the **Skills** `skill-graft vet` vets with the same arguments. It reports only: no fix, at
  most `skill-graft remove <id>` named for an **Entry**.
- It runs `skill-graft vet` for the scan. Neither its output nor the merged report reaches the main agent: their file
  names are the **Skill** author's, free text in all but spaces. The report goes to a file the user opens; the agent
  shows only numbers.
- Hardened, as the **Check** is, by the same probe: one headless reader per vetted **Skill**, `claude -p --restricted`
  with `Read`, `Grep` and `Glob`, given only that **Skill**'s deployed folder (no targets, so no **Skill** misleads
  another's reader, ASI08) and blind to the scan, replying `<file>:<line> <category>` lines and nothing else. Its turns,
  spend and readers at once take the existing `[check]` keys.
- Unhardened: the scan alone. The skill never reads **Skill** text in its own session and asks no yes to go on.
- Its own report filter merges each reader's reply with the scan in code into a report file, one line per **Flag**:
  `<skill id> <file>:<line> <category> <owasp id> <seen-by> [<pattern>]`, `seen-by` one of `scan`, `reader`, `both`, set
  by the filter, the OWASP IDs the scan's or, for a reader's own **Flag**, the category table's, never a reader's. A
  reply can only name files and lines the **Skill** has. It prints the main agent only a summary of numbers per
  **Skill**: its status, the **Flags** per category and `seen-by`, and a steering count: the scan's places, each file,
  line and category once, in a file where the reader raised none of that category.
- Fixed caveats, printed with every report, zero **Flags** included: no **Flag** is no pass; patterns are evadable;
  readers can be steered; scripts are read, never run; whether the **Vet** ran hardened, and why; reading the **Deployed
  diff** stays the user's control.
- Its own copy of `run-claude.sh`, a test keeping it identical to `graft-check`'s.
- `skill-graft vet --into <dir>`: also writes each vetted **Skill** as it would deploy to `<dir>/<alias>/<name>/`, an
  empty folder apart from any **Package**, **Source** or the cache, as `deploy --into` requires; besides the git cache
  it fetches into, the only thing `vet` ever writes. It gives the readers their folders, a **Skill** not yet added
  included.
- `evals/graft-vet/`: opt-in scenarios, never run in hooks or CI: `injected`, and `corpus`, which scores the readers
  against a labelled corpus of synthetic **Skills** (obvious harm, harm phrased past the scan, injected, harmless). A
  test runs `vet` over the same corpus, so the scan's known misses stay on record.
- `docs/security.md` (residual risks, the OWASP rows for the readers), `README.md`, `.cspell.yaml`; `CHANGELOG.md` in
  the archive commit.

## Capabilities

### New Capabilities

- `graft-vet`: the `graft-vet` skill: how it is installed and invoked, hardened or not, its readers and their reply, the
  report filter's merge and steering count, the caveats, what it never does.

### Modified Capabilities

- `vet`: an added requirement for `--into <dir>`.

## Impact

- New `skills/graft-vet/`: `SKILL.md`, `reader.json`, `run-claude.sh`, `report-filter.sh`.
- `src/skill_graft/commands/vet.py` and `cli.py`: `--into`, sharing `deploy`'s folder check.
- Tests: `tests/cli/test_graft_vet.py` (the skill, its filter, its runner), `tests/commands/test_vet.py` and
  `tests/cli/test_cli.py` (`--into`), `tests/cli/test_vet_corpus.py` (the scan over the corpus).
- New `evals/graft-vet/` (`run.sh`, `README.md`, `corpus.py`).
- `docs/security.md`, `README.md`, `.cspell.yaml`, `CHANGELOG.md` in the archive commit.

# Proposal

## Why

skill-graft deploys other people's **Skills** as written once they pass the **Hidden character** check, and
`docs/security.md` leaves judging them to the user, who must read every file of every **Skill** to see what it can make
an agent do. A **Vet** points them at the lines worth reading: each place a **Skill** may make an agent read, write or
send outside the project, run code, gain privilege, persist, widen its own permissions, or hide from review. It is the
deterministic half of the `graft-vet` skill (the `graft-vet` change), useful on its own: no agent, no tokens, the same
**Flags** on every machine. It never judges (ADR 0010).

## What Changes

- A new command, `skill-graft vet [skill-id…]`. Without arguments it vets every **Hull** **Skill**; with **Skill IDs**,
  those **Skills** and every **Skill** they reach, each a **Skill** of a declared **Source**, in the **Hull** or not:
  one outside it is vetted as its `add` would vendor it, with what it brings in.
- It computes the **Hull** as `tree` does, writes nothing, never reads the lock or runs `apm`, and scans each **Skill**
  as it would deploy, **Patches** and **Renames** applied: every file, scripts included, not only Markdown.
- A built-in pattern list, in eight categories: `read`, `write`, `send`, `run`, `privilege`, `persistence`,
  `permission`, `unreviewable`. Each category carries a fixed OWASP risk ID. `skill-graft.toml` can neither extend nor
  silence it.
- It prints one **Flag** per line, `<skill id> <file>:<line> <category> <owasp id> <pattern>`, in printable ASCII, and
  never the text it matched: its output is safe to read where **Skill** text is not.
- It exits 0 whatever it flags; it fails, as `resolve` does, only on its own errors: the config, an unknown **Skill
  ID**, a **Hidden character**, a **Patch** that does not apply.
- `docs/security.md`: its Future work item becomes the **Vet**, its residual risks and OWASP tables say what it narrows
  and what it does not.

## Capabilities

### New Capabilities

- `vet`: the `skill-graft vet` command: what it vets, which files and lines it flags, under which category and OWASP ID,
  what it prints and how it exits.

### Modified Capabilities

None: `vet` fails on **Hidden characters** because it resolves, as the `hidden-characters` spec already requires of
resolution.

## Impact

- New `src/skill_graft/pipeline/vet.py` (patterns, categories, OWASP table, the scan of one **Skill**) and
  `src/skill_graft/commands/vet.py` (the **Hull**, the **Skills** to vet, the output); `cli.py` gains the subcommand.
- `_reach` moves from `commands/edit.py` to `pipeline/hull.py`, shared by `add` and `vet`.
- Tests in `tests/pipeline/test_vet.py`, `tests/commands/test_vet.py`, and `tests/cli/test_cli.py` for the help.
- `README.md` (Commands), `docs/security.md`, `docs/architecture.md` if it lists the modules, `CHANGELOG.md` in the
  archive commit, `.cspell.yaml`. No change to resolution, the config, the lock or the vendored bytes.
- The `graft-vet` change stacks on this one; both merge once it is archived.

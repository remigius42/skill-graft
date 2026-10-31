# Proposal

## Why

Since `build` deploys only what the lock records (ADR 0009), new **Skill** text gets in through `resolve` and the
editing commands, which write the lock and the **Vendored copies** together. None of them can show that text before it
is written: `add mp/tdd` vendors `mp/tdd` and every **Skill** it reaches, and the only way to read them first is to add,
look, and `remove`. `update` already has `--dry-run --diff`; the commands through which a **Skill** first gets in have
nothing.

## What Changes

- `add`, `remove`, `rename`, `bind`, `unbind` and `resolve` gain `--dry-run`: resolve as without it and write nothing,
  printing the **Hull diff** of the **Vendored copies** against what the command would vendor, by **Skill ID**, each
  changed file named as `update` names them, then that nothing was written. Without `--diff`, a dry run that marks a
  **Skill** `+` or `~` hints `review: skill-graft <command> … --dry-run --diff <file>`.
- They gain `--diff <file>`: the **Deployed diff** of that **Hull diff**, with `update --diff`'s file and text rules,
  for an editor. With no lock, as before a **Package**'s first `add`, every **Skill** shows as added. Without
  `--dry-run` it writes the file and makes the edit, as `update --diff` does.
- Each **Deployed diff** file, `update`'s too, opens after its header with the **Hull** as `tree` prints it, each
  **Skill** marked `+` added or `~` changed, then one `# - <skill id>` line per removed **Skill**; the header's first
  line is shared, its second says what is compared.
- No `--expect` for these commands: none moves a **Ref**, so a real run right after the dry run vendors what it showed.
- `README.md`'s getting-started flow previews `add` before it writes, its patch section previews a patch with
  `resolve --dry-run`, and its Commands section is regrouped by role: staging (the commands that write the lock and the
  **Vendored copies**), deploying (`build`), inspecting and setup, the review flags explained once; `docs/design.md` and
  `docs/security.md` say how to review a change before `build`.

Out of scope, a follow-up change:

- Rename `build` to `deploy`, keeping `build` as a deprecated alias for a release. Since ADR 0009, `resolve` and the
  editing commands resolve and stage, and `build` only checks the lock and deploys.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `edit`: new requirements for the dry run, the **Hull diff** it prints, and the **Deployed diff** file.
- `resolve`: a new requirement for its dry run and diff file, as the editing commands'.
- `update`: "Deployed diff file" gains the marked tree and a header first line shared with the other commands' files.

## Impact

- A new `src/skill_graft/commands/review.py`: the diff file's refusals, header and marked tree, the **Hull diff** lines
  over two maps of hashes, the per-**Skill** sections; moved from `update.py`, which imports it. And the dry run and
  `--diff` the editing commands and `resolve` share (`review.Run`).
- `src/skill_graft/commands/edit.py` (`_finish` and each command passing `dry_run` and `diff`),
  `src/skill_graft/commands/resolve.py`: the dry run through `transaction.resolving(write=False)`, the before side read
  from the **Vendored copies** through the lock.
- `src/skill_graft/commands/explain.py`: `tree` takes a mark per **Skill**. `src/skill_graft/cli.py`: the two options on
  six commands; their dry runs write no cache.
- Tests in `tests/commands/test_review.py`, `test_edit.py`, `test_resolve.py`, `test_update.py`, `test_explain.py`.
- `CONTEXT.md`'s **Hull diff** and **Deployed diff** cover the editing commands and `resolve` (this proposal's commit).
- `README.md`, `docs/design.md`, `docs/security.md`, each command's `--help`; `CHANGELOG.md` entry at archive.

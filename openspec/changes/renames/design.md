# Design

## Context

From resolve-hull: `references.scan(folder)` yields slash and Skill tool `Reference(name, kind, text, file)` from
one regex; `hull.walk` resolves them (own **Source**, one other, **Binds**), BFS from the **Entries**, and returns
`Hull(skills, entries, edges, warnings)`; `resolve.resolve` checks deployed names (= names) before and after the
walk; `vendor.vendor(skills)` copies to `.apm/skills/<name>/`; `lock.render` hashes each folder, `build` hashing
the vendored copies; `lock.tree` prints one line per (target, kind, bind). Tests: `tests/conftest.py` (`skill`,
`configure`, `write_config`, `Upstream`, `HOME` in `tmp_path`).

## Goals / Non-Goals

**Goals:** one place deciding **Deployed names** and rewrites, shared by `resolve` (hash, tree) and `build`
(files); every name error before any write; the vendored bytes a pure function of the **Source** folders and the
TOML.

**Non-Goals:** rewriting non-Markdown files or non-UTF-8 Markdown; parsing Markdown (no code-span or fence
awareness beyond the regex); YAML beyond the `name:` line.

## Decisions

- **Prose in the same regex**: two more alternatives after slash and Skill tool in `references.REFERENCE`:
  `` (?<!`)`(?P<code>NAME)`(?!`) `` and the hyphenated token with the slash boundaries plus `(?![\w/-]|[.:]\w)`.
  One leftmost scan means `` `/grilling` `` and `Skill(diagnosing-bugs)` yield one **Reference**, never a prose
  one inside. `Reference` gains `kind = "prose"` and `span`: the name's offsets in the decoded text, for rewriting.
  Alternative, a second pass for prose: overlaps must then be removed by hand.

- **Prose resolves after the walk**: whether a prose target is in the **Hull** is known only when the BFS ends.
  The walk records each prose **Reference** with its candidate (**Bind**, else `a/<name>` if
  `index.folders` has it, else dropped; `unreadable` names do not count, as prose must not raise); afterwards a
  candidate in the **Hull** becomes a `prose` edge, any other a suggestion (suggested `SkillId` → the `SkillIds`
  mentioning it). A **Bind** used by prose counts as used. A bound prose target is checked with `discovery.find` like
  any bound target, so a missing one is the same error.

- **Every occurrence kept**: the walk also returns `occurrences: dict[SkillId, list[(Reference, SkillId)]]`,
  every resolved **Reference** in that **Skill** with its target, self-**References** included (they get no
  edge but are rewritten). Rewriting needs spans per file; edges stay deduplicated for the lock.

- **`rename.py`** owns names:

  - `deployed(config, skills) → dict[SkillId, str]`; unused `[rename]` keys → warnings.
  - `check(config, deployed)`: uniqueness ignoring case (error naming both and `[rename] "<id>" = "<alias>-<name>"`
    for the later one), the user's `reserved` (error), `SHIPPED` (warning; suggestion only when not renamed).
    Called on the **Entries** before the walk (cheap early clash) and on the **Hull** after it, replacing
    `resolve._check_deployed_names`.
  - `rewrites(hull, deployed) → dict[SkillId, dict[Path, bytes]]`: per **Skill**, the relative paths whose bytes
    change. For each UTF-8 Markdown file, replace the spans of occurrences whose target's **Deployed name** differs
    from the written name, back to front; for a renamed **Skill**, `SKILL.md` gets `set_name`. Files that end up
    unchanged are left out.
  - `set_name(text, name)`: line-based on the front matter `discovery.read_name` reads (BOM and line endings kept):
    replace the `name:` line, else insert after the opening `---`, else prepend `---\nname: x\n---\n`.
  - `SHIPPED`: a sorted tuple of names, Claude Code's built-in commands and bundled skills (`agents`, `clear`,
    `code-review`, `compact`, `config`, `context`, `doctor`, `help`, `hooks`, `init`, `loop`, `mcp`, `memory`,
    `model`, `resume`, `review`, `schedule`, `security-review`, `simplify`, …) and Codex's (`diff`, `status`, …).
    Matched by `casefold`.

- **Hull carries names**: `Hull` gains `deployed`, `occurrences`, `suggestions`, and `rewrites`, filled by
  `resolve.resolve`, so `resolve`, `build` and `update` share them.

- **Vendor**: `vendor.vendor(hull)` copies each folder to `skills.new/<deployed>/`, then writes `rewrites` over the
  copy, before the swap; a failure still leaves `.apm/skills/` as it was. Writing after `copytree` keeps the copy
  code unchanged; a rewritten file keeps the upstream file's mode (it is overwritten in place).

- **Hash**: `lock.folder_hash(folder, overrides)` hashes `overrides[path]` instead of the file's bytes where
  given. `resolve` passes the rewrites; `build` keeps hashing the vendored copies (now under deployed names), which
  are the same bytes by construction; a test pins `resolve` lock == `build` lock. Alternative, hashing upstream
  bytes: a changed rename would not show in the lock.

- **Lock**: `[[skills]]` gains `deployed` only when renamed; edges gain kind `prose`; new `[[suggestions]]` with
  `id` and sorted `from` list, sorted by `id`. Still `version = 1`: the lock is output only.

- **Tree**: a node is `<id>` or `<id> as <deployed>`; labels as written upstream; `prose` edges filtered out
  unless the target is renamed, label `` `name`, prose ``. Suggestions printed by `cli` after the tree:

  ```text

  mentioned in prose, not in the hull (add to entries to include):
    mp/diagnosing-bugs, by mp/tdd
  ```

  When `add` lands (explain-and-edit), the hint becomes the command.

## Risks / Trade-offs

- \[A renamed **Skill** whose name is also a command in a code block of its own **Source** (`pre-commit run`) is
  rewritten\] → `"mp/pre-commit" = false`, which also drops real **References** to it from that **Source**; a
  prose-only **Bind** if it bites.
- [Hyphenated prose matches ordinary compounds] → only when the own **Source** has a **Skill** of exactly that
  name, and it does nothing unless the target is renamed or outside the **Hull** (a suggestion).
- \[`SHIPPED` goes stale as harnesses add commands\] → a warning only; the user's `reserved` covers the gap.
- [Rewriting by span on decoded text] → re-encoded as UTF-8; the only bytes that change are the replaced names
  (and a BOM is kept as read).

## Migration Plan

Configs without `[rename]` or `reserved` load unchanged. Two visible changes on the next `build`: a bound
**Reference** naming another **Skill** name is rewritten (lock hashes of such **Skills** change once), and a
**Hull** **Skill** named like a shipped **Reserved name** warns. `docs/design.md` and `README.md` follow.

## Open Questions

- The exact `SHIPPED` contents: checked against the current Claude Code and Codex docs during task 3.1; any name
  added later only adds a warning.

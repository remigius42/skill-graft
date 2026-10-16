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
  `` (?<!`)`(?P<code>NAME)`(?!`) `` and the hyphenated token with the slash lookbehinds (`[\w./:~\\<@-]`, `](`,
  `="`, `='`) and `(?![\w/-]|[.:]\w)`, exactly the boundaries the hull spec lists.
  One leftmost scan means `` `/grilling` `` and `Skill(diagnosing-bugs)` yield one **Reference**, never a prose
  one inside. `Reference` gains `kind = "prose"` and `span`: the offsets in the decoded text of the name alone (a slash
  name's trailing dots excluded, as `scan` strips them), for rewriting. The front matter `name:` value of
  `SKILL.md` is skipped, so a **Bind** on a **Skill**'s own name never rewrites its `name:`.
  Alternative, a second pass for prose: overlaps must then be removed by hand.

- **Prose resolves after the walk**: whether a prose target is in the **Hull** is known only when the BFS ends.
  The walk records each prose **Reference** with its candidate (**Bind**, else `a/<name>` if
  `index.folders` holds exactly one folder for it and `index.unreadable` none, else dropped: prose never raises,
  and a suggestion must be addable); afterwards a
  candidate in the **Hull** becomes a `prose` edge, any other a suggestion (suggested `SkillId` → the `SkillIds`
  mentioning it). A **Bind** used by prose counts as used. A bound prose target is checked with `discovery.find` like
  any bound target, so a missing one is the same error.

- **Every occurrence kept**: the walk also returns `occurrences: dict[SkillId, list[(Reference, SkillId)]]`,
  every resolved **Reference** in that **Skill** with its target, self-**References** included (they get no
  edge but are rewritten). Rewriting needs spans per file; edges stay deduplicated for the lock.

- **`rename.py`** owns names:

  - `unused(config, skills)`: a warning per `[rename]` key naming no hull skill. (`config.deployed(config, skill)`
    gives a skill's name, so `hull.walk` fills `Hull.deployed` without importing `rename`.)
  - `check_unique` and `check_reserved`: uniqueness ignoring case, the user's `reserved` (error), `SHIPPED`
    (warning; suggestion only when not renamed). A hint never adds a second key: it names an unrenamed skill, or
    says which `[rename]` value to change.
    Called once, on the **Hull** after the walk, replacing `resolve._check_deployed_names`; before the walk only
    the uniqueness error runs on the **Entries** (cheap early clash, no warnings, so none is wrong or doubled).
  - `rewrites(hull, deployed) → dict[SkillId, dict[Path, bytes]]`: per **Skill**, the relative paths whose bytes
    change. For each UTF-8 Markdown file, replace the spans of occurrences whose target's **Deployed name** differs
    from the written name, back to front; for a renamed **Skill**, `SKILL.md` gets `set_name`. Files that end up
    unchanged are left out.
  - `set_name(text, name)`: line-based on the front matter `discovery.read_name` reads (BOM and line endings kept):
    replace the `name:` line, else insert after the opening `---`, else prepend `---\nname: x\n---\n`. The value
    is double-quoted unless it is `[a-z][a-z0-9-]*` and not a YAML 1.1 bool or null word (`y`, `no`, `on`, …).
  - `SHIPPED`: a sorted tuple of names, Claude Code's built-in commands and bundled skills (`agents`, `clear`,
    `code-review`, `compact`, `config`, `context`, `doctor`, `help`, `hooks`, `init`, `loop`, `mcp`, `memory`,
    `model`, `resume`, `review`, `schedule`, `security-review`, `simplify`, …) and Codex's (`diff`, `status`, …).
    Matched by `casefold`.

- **Hull carries names**: `Hull` gains `deployed`, `occurrences` and `suggestions`, filled by `hull.walk`.
  `rename.rewrites(hull)` is a function, called where bytes are needed (vendor, lock hash, update diff), not stored:
  `update` resolves twice, and its previous **Hull** needs only hashes.

- **Vendor**: `vendor.vendor(hull)` copies each folder to `skills.new/<deployed>/` with `copytree` and a
  `copy_function` that writes the rewritten bytes (then `copymode`) for a rewritten path and `copy2`s any other,
  before the swap; a failure still leaves `.apm/skills/` as it was. No file is opened twice and `copytree` applies
  folder modes last, so a read-only upstream file or folder (`0444`, `0555`, a Nix store) never blocks a rewrite.
  Alternative, writing over the copy afterwards: fails on read-only copies.

- **Hash**: `lock.folder_hash(folder, overrides)` hashes `overrides[path]` instead of the file's bytes where
  given; `lock.skill_hashes(hull)` applies each **Skill**'s rewrites, and `lock.render` uses it unless given
  hashes, so `resolve` and `update` (lock and hull diff) hash alike. `build` keeps hashing its vendored copies, as
  resolve-hull pinned (the lock holds exactly what was vendored), now found by **Deployed name**; the bytes match by
  construction, and a test pins `resolve` lock == `build` lock. Alternative, hashing upstream bytes: a changed
  rename would not show in the lock.

- **Lock**: `[[skills]]` gains `deployed` only when renamed; edges gain kind `prose`; new `[[suggestions]]` with
  `id` and sorted `from` list, sorted by `id`. Still `version = 1`: the lock is output only.

- **Tree**: a node is `<id>` or `<id> as <deployed>`; labels as written upstream (`` `name` `` or bare `name`);
  a `prose` edge shown only when rewritten (target's **Deployed name** ≠ name written: renamed or bound), label
  `<as written>, prose[, bind]`. Suggestions printed by `cli` after the tree:

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
- \[A relative link into a renamed **Skill**'s folder (`../diagnosing-bugs/SKILL.md`) is not rewritten\] → out of
  scope: a **Skill** is its own folder, and such links already break when the upstream layout differs from the
  flat `.apm/skills/`; a **Patch** (next change) fixes one.
- \[Prose naming a **Skill** that a slash **Reference** reached in another **Source** stays as written: `/notes`
  becomes `/own-notes` while `` `notes` `` beside it does not\] → ADR 0002: prose never looks across **Sources**;
  a **Bind** `"mp/notes" = "own/notes"` makes the prose follow.
- [Rename values follow the name pattern, not the stricter Agent Skills one (lowercase, hyphens)] → as agreed: a
  rename is no stricter than names vendored unrenamed; APM reports one it rejects.
- \[`SHIPPED` goes stale as harnesses add commands\] → a warning only; the user's `reserved` covers the gap.
- [Rewriting by span on decoded text] → re-encoded as UTF-8; the only bytes that change are the replaced names
  (and a BOM is kept as read).

## Migration Plan

Configs without `[rename]` or `reserved` load unchanged. Two visible changes on the next `build`: a bound
**Reference** naming another **Skill** name is rewritten (lock hashes of such **Skills** change once), and a
**Hull** **Skill** named like a shipped **Reserved name** warns. `docs/design.md` and `README.md` follow.

## Open Questions

- The exact `SHIPPED` contents: checked against the current Claude Code and Codex docs during task 4.2; any name
  added later only adds a warning.

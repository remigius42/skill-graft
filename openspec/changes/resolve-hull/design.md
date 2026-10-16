# Design

## Context

From git-sources: `resolve.folders(config, cache, refs)` checks out only the **Sources** an **Entry** uses;
`resolve.resolve(config, folders)` checks deployed names, `discovery.find`s each **Entry** and checks symlinks;
`vendor.vendor(resolved)` copies and swaps. `update` calls both with the new tips. `discovery.find` words its
errors for an **Entry**. `config.load` rejects every top-level key but `sources` and `entries`. Tests build
synthetic path **Sources** (`skill`, `configure`) and git ones (`Upstream`), `HOME` in `tmp_path`.

## Goals / Non-Goals

**Goals:** one resolution step shared by `resolve`, `build` and `update`; deterministic output (lock bytes, tree
order, warnings); every error before any write.

**Non-Goals:** prose detection, lazy reading of **Sources**, reading the lock back, incremental resolution.

## Decisions

- **Modules**: `references.py` scans one **Skill** folder → ordered list of `Reference(name, kind, file)`;
  `hull.py` resolves and walks; `lock.py` renders the lock and the tree. `resolve.py` keeps `check_refs` and
  `folders`, now over every declared **Source**, and its `resolve()` returns a `Hull`: ordered skills
  (`SkillId → Path`), entries, edges `(from, to, kind, bind, reference)`, warnings. `vendor` takes `Hull.skills`.

- **Scan**: only after `check_files` passed for that **Skill** (links stay inside, no FIFO or device), so none is ever
  opened. Every `*.md` (case-insensitive) under the folder, `.git` skipped, files in sorted relative-path order
  with `SKILL.md` first; references in text order. Not UTF-8 → warning, file skipped. Slash regex, roughly
  `(?<![\w./:~\\<@-])(?<!\]\()(?<!=["'])/([A-Za-z0-9][A-Za-z0-9._-]*+)(?!/|:\w)` (no link targets,
  attributes or `@/` aliases): the possessive `*+` (Python 3.11) keeps the run
  whole, so `/my-dir/file` never yields `my`; trailing dots are dropped after matching. Skill tool:
  `\bSkill\(\s*(?:skill\s*[:=]\s*)?(["']?)(NAME)\1\s*[,)]`, so further arguments are allowed. Names match
  case-sensitively. A file that cannot be opened (dangling link) raises `SkillGraftError` naming it. Each reference
  keeps its text as written for warnings.
  Code blocks count: a missed **Reference** is silent and only a **Patch** fixes it; a false one is loud (a
  warning or a tree line) and one `"<alias>/<name>" = false` **Bind** per **Source** silences it, so the
  warning names that line. Alternative, skipping fenced blocks: misses `/grilling` in example invocations.

- **Resolution** per reference from `a/x` to `name`: a **Bind** `a/name` wins (`false`: dropped, no edge, no
  warning, but it counts as used); else `a` has `name` → `a/name`;
  else exactly one other alias has it → that; several → error with the `[bind]` hint; none → warning. "Has"
  means the **Source**'s `Index` holds the name in `folders` or `unreadable`, so an unreadable **Skill**
  surfaces its error instead of being skipped. Not `invalid`: as `discovery.find` says, an invalid name is known
  not to be this one. Then `find` (generalized with a `who` label, e.g.
  `entry 'mp/tdd'` or `'mp/tdd' calls /grilling`) gives the folder. BFS from the **Entries** in TOML order;
  each **Skill** scanned once; an edge whose target, **Binds** applied, is its source is dropped. Edge kind is the form,
  `slash` or `skill-tool`, plus a `bind` flag when a **Bind** decided it, so `why` can say both how it is called and what
  redirected it. Alternative, a third kind `bind` (as `docs/design.md` had): loses the form.

- **Index every Source eagerly**: "exactly one other" needs every other index whenever the own **Source** misses,
  which unmatched names make the usual case. Cost: a declared but unused git **Source** with an uncached `ref`
  is now fetched by `build`; `check_refs` already demanded its `ref`.

- **Lock format**: TOML via `tomlkit` (already a dependency, so no JSON-vs-TOML split in user files):

  ```toml
  # Written by skill-graft; never read. Do not edit.
  version = 1

  [sources.mp]
  git = "https://…"
  ref = "<sha>"

  [sources.own]
  path = "/home/u/skills"

  [[skills]]
  id = "mp/tdd"
  entry = true
  hash = "sha256:<hex>"

  [[edges]]
  from = "mp/tdd"
  to = "mp/grilling"
  kind = "slash"

  [[edges]]
  from = "mp/tdd"
  to = "own/notes"
  kind = "skill-tool"
  bind = true
  ```

  Sources sorted by alias, skills by ID, edges by (from, to, kind, bind); an edge is unique on all four, so a
  bound and a default **Reference** to one **Skill** are two edges. Always at `paths.package()/skill-graft.lock`,
  never beside a symlinked TOML's target: it is local output with absolute paths. Written to a temp file there,
  then
  `os.replace`. Hash: SHA-256 over each file as vendored (`.git` skipped, symlinks followed), in sorted order
  of the relative path as `/`-separated `os.fsencode` bytes: `path NUL exec-bit NUL length NUL bytes`. That is
  what lands in `.apm/skills/`, so it matches whatever APM sees.

- **Tree**: `cargo tree` proper. DFS from each **Entry** over edges in scan order, one line per edge; a
  **Skill** expanded at its first line, later lines marked `(*)`; **Entries** marked `(*)` wherever nested, as
  they expand at the top level. Lines = **Entries** + edges, so size stays linear. Box characters as
  `cargo tree` (`├──`, `└──`, `│`). Label: `/name` or `Skill(name)`, plus `, bind`. Alternative, one line per
  **Skill** under its first parent: shorter, but shows one reason per **Skill**, not all.

- **Command wiring**: `resolve` = load → folders → resolve → write lock → print tree (stdout), warnings
  (stderr, `skill-graft: warning:` like config warnings). `build` = same minus the tree, then vendor, then write
  the lock, then APM: the lock describes what `.apm/skills/` holds. `update` = resolve at new tips (errors as
  today) → if old `ref`s all exist and are cached (`has_commit`, real cache; never fetched), resolve again at
  them, its warnings dropped, and diff skill sets and hashes, else print "no previous hull to compare" with the
  reason → write the lock always and the TOML when a `ref` moved (neither on `--dry-run`, whose message names
  both): a path **Source** can change while no `ref` moves. Resolving the old `ref`s twice beats reading the
  lock, which would make it an input. An old resolution error only replaces the diff with that note.

## Risks / Trade-offs

- \[Slash false positives (`cd /tmp`) add warnings\] → a `false` **Bind** per **Source**, named in the warning.
- \[The Skill tool form is guessed from the call syntax; packs that say "use the Skill tool to run `x`" are
  missed\] → prose **References** (next changes) cover backticked names in the own **Source**.
- \[Eager reading fetches unused git **Sources**\] → only when their `ref` is missing; they are declared intent.
- \[`update` resolves twice\] → old commits are cached; a few hundred ms for skill repositories.
- \[Path **Source** lock entries hold absolute home paths\] → the lock is local provenance, not shared; its
  determinism is per machine.
- \[A non-UTF-8 Markdown file hides its **References**\] → a warning names it; the file is still vendored.

## Migration Plan

Configs without `[bind]` load unchanged. Two behavior changes: `build` vendors more skills for packs with slash
references, which is the point; and since every declared **Source** is read, `build` now fails on an unused one
it ignored before: a git **Source** whose `ref` is uncached and cannot be fetched (offline). (A path **Source**
whose folder is gone already fails at load.) Remove the unused **Source** to go back. `docs/design.md`: add the lock
format and the Skill tool form.

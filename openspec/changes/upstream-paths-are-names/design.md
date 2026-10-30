# Design

## Context

`discovery.index` walks a **Source**'s folder (a git **Source**'s `subdirectory`, when set) and files each **Skill** in
an `Index`: `folders` by name, `unreadable` (a **Skill** that may have that name: `find` raises its error, `_has` counts
it, so a slash or `Skill(<name>)` **Reference** never resolves past it, and `_prose_target` skips it, so a prose or
Skill tool sentence one stays a word) and `invalid` (a name that is no path segment, known not to be the one asked: it
only explains a miss). The lock records `upstream` relative to `hull.roots`, the tree's root, so for a git **Source**
with `subdirectory` it is `<subdirectory>/<path below it>`, and `.` for a **Skill** at the root
(`test_skill_at_the_source_root`). `_relative_folder` in `config.py` checks `subdirectory`. graft-check reads the lock
with its file tool in step 2.

## Goals / Non-Goals

**Goals:**

- Every segment of the lock's `upstream` matches `[A-Za-z0-9._-]+`, not only dots, or it is `.`, so no author-chosen
  folder name can carry a line break, a space, shell syntax or a non-ASCII character to the **Check**'s agent, neither
  through the lock nor through an error.
- graft-check refuses a lock that breaks this before reading it, against a skill-graft older than this change.

**Non-Goals:**

- File names inside a **Skill**'s folder. The agent never sees them: a report's `file` is quoted data, and the patcher's
  diff summary holds numbers only.
- Prose injection in words made of the allowed characters. **Skill** names already open that channel, and the agent
  already holds them.
- A lock edited by hand into another TOML layout. The **Check** reads the lock its own throwaway build just wrote; the
  threat is an older skill-graft, which writes tomlkit's layout. A line in another layout still counts as bad.
- Quoting `why`'s `upstream:` line. Below the root it now holds only allowed characters; the root is the cache's or the
  user's own folder, and quoting a root with a space would break graft-check taking the lock's `upstream` off the line's
  end.
- A command printing a **Source**'s root only. The agent still needs the full **Upstream** folder for `--add-dir` and
  `cp -rL`, and once the segments are checked it can build that folder safely.

## Decisions

**One segment pattern, `SEGMENT`, in `config.py`.** `\.*[A-Za-z0-9_-][A-Za-z0-9._-]*`: `[A-Za-z0-9._-]+` with a
character other than a dot. Unlike `NAME`, a segment may start with `.`, since `.claude/skills/` and `.agents/skills/`
are common layouts and discovery walks hidden folders, and with `-` or `_`: every path built from a segment starts at an
absolute root or a key's value, never as an argument of its own, so `-rf` cannot be read as an option. Neither `.` nor
`..` can match, so `_relative_folder` drops those checks and its control-character check; it keeps `.git` and the
package check. Its error names the rule: expected a folder relative to the repository root, like `skills`, its parts of
`A-Z a-z 0-9 . _ -`, not only dots, no `.git` part, not into a package. Rejected: `NAME` for folders too, which would
refuse every **Skill** under `.claude/`.

**Checked in `index`, relative to the walked folder.** The walk yields each path as reached, symlinks unresolved, which
is what the lock records. A **Skill** at the walked folder has no parts (`Path(".")`'s `parts` is empty) and passes.
`subdirectory`, the rest of the lock's `upstream`, is checked at load. Rejected: checking in `lock.render`, which would
fail the whole build for one bad folder anywhere in the hull, and only once written.

**A bad path files as `unreadable`, after `_check`.** Its name may well be the one asked: `own/tdd` at `my skills/tdd/`
is named `tdd`. As `unreadable`, an **Entry** naming it gets the path error, a slash or `Skill(<name>)` **Reference** to
it in its own **Source** errors rather than resolving in another one, a Skill tool sentence stays a word, a clean
namesake makes it ambiguous, and it blocks nothing else. The same holds for a `[bind]` target and `add`'s check, which
reach `find` too. The order per folder: `_check` (regular file, confined symlink), then the path. A good path goes on as
today. A bad path files the path error and no other: when `_check` passed, `read_name` only picks the key, the name when
it reads and matches `NAME`, else the folder name; when `_check` failed, `read_name` is never called and the key is the
folder name. So no error naming a bad path carries it raw. Rejected: `invalid`, which `_has` skips, so `/tdd` would
silently resolve to another **Source**'s `tdd`.

**The error escapes every byte outside `[A-Za-z0-9._/-]` as octal.**
`<walked folder>: skill folder <escaped path> uses characters outside A-Z a-z 0-9 . _ -`, the path's `os.fsencode` bytes
with each such byte written `\ooo`: `my\040skills/tdd`, `\044\050id\051` for `$(id)`, `\303\244` for `ä`; an undecodable
byte, held as a surrogate, escapes as the byte it was. The walked folder is trusted: the cache's or the user's. The same
helper escapes the name and the path in the existing `invalid` error (`name '$(curl x)/a' is not one path segment`
today), the other error that holds author text. Rejected: `deployed.quote`, which leaves `$`, `(`, backticks and `;` as
they are, so shell syntax would reach the agent through the build error graft-check shows. The helper lives in
`discovery`, which needs no new import.

**graft-check checks the lock with one `awk` that prints its version and a count, and exits 0.** Before step 2 reads the
lock:

```sh
LC_ALL=C awk '
  BEGIN { n = "[A-Za-z0-9][A-Za-z0-9._-]*"; id = "\"" n "/" n "\""; v = "none"
          s = "\\.*[A-Za-z0-9_-][A-Za-z0-9._-]*"; p = "\"[^\"\\\\]*\"" }
  /^\[/ { t = $0
          if (t !~ /^\[\[(skills|edges|suggestions)\]\]$/ && t !~ "^\\[sources\\." n "\\]$") { bad++; t = "[[skills]]" }
          next }
  t == "" && /^version = [0-9]+$/ { v = $3; next }
  /^$/ || t ~ /^\[sources\./ || t == "" && /^# Written by skill-graft; update reads its hashes\. Do not edit\.$/ { next }
  t != "" && ($0 ~ "^(id|from|to) = " id "$" || $0 ~ "^deployed = \"" n "\"$" \
    || $0 ~ "^upstream = \"(\\.|" s "(/" s ")*)\"$" || $0 ~ "^from = \\[" id "(, " id ")*\\]$" \
    || $0 ~ "^patches = \\[(" p "(, " p ")*)?\\]$" || /^(entry|bind) = (true|false)$/ \
    || /^kind = "(slash|skill-tool|prose)"$/ || /^hash = "sha256:[0-9a-f]+"$/) { next }
  { bad++ }
  END { printf "version: %s, bad: %d\n", v, bad }' <lock>
```

Every line of the lock must be blank, the header comment, `version`, a header of `[sources.<name>]` or one of the three
tables, a line under `[sources.<name>]`, which holds the user's own config, or one of the forms above under the three
tables. A header in any other form counts and keeps checking on, so a later bad value cannot hide behind it. `patches`
lists the user's own config, but as plain strings only, so no second key can follow on its line. tomlkit writes each key
on its own line, strings in basic quotes, so a value holding a quote, an escape or a line break fails its form. The
skill reads the version first: one other than 1 takes the "Lock version" path, as today, since a newer lock may hold
keys this command does not know; then a count above 0 ends the **Check**. `awk` exits 0 whatever it finds, so the
skill's "a non-zero exit ends the **Check**" keeps meaning a failure. The exact forms are pinned by 3.1's test against a
lock a real build writes. Rejected: reading the lock and then judging its values, which already puts them in the agent's
context; a `grep -cv` pipeline, which exits 1 on a clean lock.

**A git Source's root from `why` when `upstream` is `.`.** graft-check takes the lock's `upstream` off the end of
`why`'s `upstream:` line to find the root; for a **Skill** at the root, the line is the root itself (`Path` drops a
trailing `/.`). Step 3 says so.

## Risks / Trade-offs

- \[A path **Source** of the user's own, holding a **Skill** under `my skills/`, stops building\] → the error names the
  folder; renaming it fixes it. The changelog says so.
- [A git repository whose skills sit under a folder with a space or non-ASCII name cannot be grafted] → no workaround
  but a fork; such layouts are rare among skill repositories.
- [A later lock key, or a tomlkit layout change, makes graft-check refuse every lock] → 3.1's test runs the command on a
  real build's lock, so the change that adds the key fails until it updates the command.
- \[`awk` versions differ\] → POSIX `awk` with dynamic regexes and `LC_ALL=C` only; macOS's `awk` runs in CI.
- \[The walk visits each resolved folder once, in sorted order, so a real folder with a bad name that sorts first (a
  space or `$` sorts before letters) hides a well-named symlink to the same **Skill**\] → accepted: rare, and the error
  names the folder; a path **Source** renames it, a git one needs a fork.

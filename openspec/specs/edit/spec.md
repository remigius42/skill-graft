# edit Specification

## Purpose

`skill-graft add`, `remove`, `rename`, `bind` and `unbind` change the **Entries**, **Renames** and **Binds** in
`skill-graft.toml` for the user, checking that the result resolves before anything is written.

## Requirements

### Requirement: Resolve before writing

`add`, `remove`, `rename`, `bind` and `unbind` SHALL compute the **Hull** of the edited config, as `resolve` does,
before writing anything. Only if that succeeds SHALL they write `skill-graft.toml`, then vendor `.apm/skills/` and write
`skill-graft.lock` together, as `resolve` does, and print what `resolve` prints. A failure SHALL exit 1 and leave the
TOML, the lock and `.apm/skills/` unchanged; so SHALL an interrupt while they are written, but exit as interrupted. If
restoring `skill-graft.toml` fails too, a notice SHALL name it and the error, and the original error SHALL be the one
reported. They SHALL NOT run `apm`. When the command changes no value (every **Skill ID** given is a no-op, or `bind`'s
target is the current value), it SHALL print only its notices, exit 0, and neither resolve nor write anything.

#### Scenario: Edit succeeds

- **WHEN** the user runs `skill-graft add mp/notes` and the edited config resolves
- **THEN** `entries` holds `mp/notes`, the lock is rewritten, `.apm/skills/notes/` holds `mp/notes`, the tree is
  printed, and `apm` is not run

#### Scenario: Edit fails to resolve

- **WHEN** the user runs `skill-graft add mp/notes` and `mp/notes` calls `/x`, which matches several other **Sources**
  and no **Bind**
- **THEN** it exits non-zero, and `skill-graft.toml`, `skill-graft.lock` and `.apm/skills/` keep their bytes

#### Scenario: Lock write interrupted

- **WHEN** the user runs `skill-graft add mp/notes`, the edited config resolves, and the user presses Ctrl-C while
  `skill-graft.lock` is written
- **THEN** `skill-graft.toml`, `skill-graft.lock` and `.apm/skills/` keep their bytes

### Requirement: Edit the TOML in place

An edit SHALL change only the values it is about, keeping every other comment, blank line, key order and other
formatting, and SHALL replace the file atomically. A symlinked `skill-graft.toml` SHALL stay a symlink: its target is
what changes, and relative paths in it resolve as `load` resolves them. A command that changes no value SHALL NOT
rewrite the file. A removed value's own trailing comment goes with it.

#### Scenario: Comments survive

- **WHEN** `skill-graft.toml` has comments, one trailing an existing `[rename]` line, and the user runs
  `skill-graft rename mp/tdd mp-tdd2` over that line's value
- **THEN** the new file equals the old one with only that value replaced

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink and the user runs `skill-graft add mp/notes`
- **THEN** it is still that symlink, and the file it points to holds `mp/notes`

### Requirement: Notices

Notices SHALL go to standard error with the warnings and SHALL NOT change the exit code.

#### Scenario: Notice stream

- **WHEN** `skill-graft add mp/tdd` finds `mp/tdd` already an **Entry**
- **THEN** standard error names `mp/tdd` as already an **Entry**, and standard output holds no notice

### Requirement: Add entries

`add <skill-id>…` SHALL append each **Skill ID** to `entries` in the order given, keeping the array's style, and SHALL
create `entries` before the first table when it is absent. A **Skill ID** given twice SHALL be added once.

#### Scenario: Appended

- **WHEN** `entries = ["mp/tdd"]` and the user runs `skill-graft add own/chisel mp/notes`
- **THEN** `entries` is `["mp/tdd", "own/chisel", "mp/notes"]`

#### Scenario: Multi-line array

- **WHEN** `entries` is written one **Skill ID** per line with a trailing comma, and the user runs
  `skill-graft add mp/notes`
- **THEN** `mp/notes` is on a new line after the last one, with a trailing comma

#### Scenario: No entries key

- **WHEN** `skill-graft.toml` has `[sources.mp]` and no `entries`, and the user runs `skill-graft add mp/tdd`
- **THEN** `entries = ["mp/tdd"]` stands before `[sources.mp]`

### Requirement: Add checks the skill

`add` SHALL refuse a **Skill ID** that is malformed, has an undeclared alias, or names no **Skill** in its **Source**,
writing nothing. A **Skill ID** already an **Entry** SHALL be a notice and left alone. A **Skill** already in the
**Hull** before the edit SHALL be added, with a notice naming a **Skill** whose slash or Skill tool **Reference**
reached it then; **Skill IDs** added by the same command do not count.

#### Scenario: Unknown skill

- **WHEN** **Source** `mp` has no **Skill** `nope` and the user runs `skill-graft add mp/notes mp/nope`
- **THEN** it exits non-zero naming `mp/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Undeclared alias

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft add zz/tdd`
- **THEN** it exits non-zero naming the alias `zz`

#### Scenario: Already an entry

- **WHEN** `mp/tdd` is an **Entry** and the user runs `skill-graft add mp/tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes and modification time

#### Scenario: Already reachable

- **WHEN** **Entry** `mp/tdd` calls `/grilling` and the user runs `skill-graft add mp/grilling`
- **THEN** `entries` holds `mp/grilling`, and a notice says it was already in the **Hull** via `mp/tdd`

#### Scenario: Added together

- **WHEN** neither `mp/a` nor `mp/b` is in the **Hull**, `mp/a` calls `/b`, and the user runs
  `skill-graft add mp/a mp/b`
- **THEN** `entries` holds both and no notice is printed

#### Scenario: Reached only through itself

- **WHEN** `mp/x` calls `/y`, `mp/y` calls `/x`, no **Entry** reaches either, an **Entry** mentions `x` in prose, and
  the user runs `skill-graft add mp/x`
- **THEN** `entries` holds `mp/x` and no notice is printed

### Requirement: Remove entries

`remove <skill-id>…` SHALL delete each **Skill ID** from `entries`, keeping the array's style. A **Skill ID** that is no
**Entry** SHALL be an error, writing nothing. A removed **Skill** still in the **Hull** SHALL be a notice naming a
**Skill** whose slash or Skill tool **Reference** reaches it from the remaining **Entries**. Removing the last **Entry**
SHALL leave `entries = []`, an empty **Hull**.

#### Scenario: Last entry

- **WHEN** `entries = ["mp/tdd"]` and the user runs `skill-graft remove mp/tdd`
- **THEN** `entries = []`, the lock holds no **Skills**, and the printed tree is empty

#### Scenario: Removed

- **WHEN** `entries = ["mp/tdd", "mp/notes"]`, no **Skill** reaches `mp/notes`, and the user runs
  `skill-graft remove mp/notes`
- **THEN** `entries` is `["mp/tdd"]` and the printed tree has no `mp/notes`

#### Scenario: Not an entry

- **WHEN** `mp/grilling` is no **Entry** and the user runs `skill-graft remove mp/grilling`
- **THEN** it exits non-zero naming `mp/grilling`, and `skill-graft.toml` is unchanged

#### Scenario: Still reachable

- **WHEN** **Entries** `mp/tdd` and `mp/grilling`, `mp/tdd` calling `/grilling`, and the user runs
  `skill-graft remove mp/grilling`
- **THEN** `entries` is `["mp/tdd"]`, and a notice says `mp/grilling` stays in the **Hull** via `mp/tdd`

### Requirement: Rename a skill

`rename <skill-id> <name>` SHALL set the **Skill**'s value in `[rename]`, replacing an existing value in place or
appending a key, and SHALL append a `[rename]` table at the end of the file when it is absent. `<name>` SHALL be a valid
**Skill** name. A `<name>` equal to the current **Deployed name** SHALL be a notice and change nothing.

#### Scenario: New rename

- **WHEN** there is no `[rename]` table and the user runs `skill-graft rename mp/code-review mp-code-review`
- **THEN** the file ends with a `[rename]` table holding `"mp/code-review" = "mp-code-review"`, and the tree shows
  `mp/code-review as mp-code-review`

#### Scenario: Already that name

- **WHEN** `mp/tdd` is renamed to `mp-tdd` and the user runs `skill-graft rename mp/tdd mp-tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already the prefixed name

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, no `[rename]` key names `mp/tdd`, and the user runs
  `skill-graft rename mp/tdd mp-tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Invalid name

- **WHEN** the user runs `skill-graft rename mp/tdd a/b`
- **THEN** it exits non-zero naming `a/b`, and `skill-graft.toml` is unchanged

### Requirement: Undo a rename

`rename <skill-id> <name>` with `<name>` equal to what the **Skill** deploys as without a `[rename]` key (its
**Source**'s `prefix` followed by its name, else its name) SHALL remove its `[rename]` key, leaving the table in place
even if empty. Any other `<name>`, the upstream name under a **Prefix** included, SHALL be written as a key.

#### Scenario: Undone

- **WHEN** **Entry** `mp/code-review` is renamed to `mp-code-review` and the user runs
  `skill-graft rename mp/code-review code-review`
- **THEN** `[rename]` no longer holds `mp/code-review`, and the shipped reserved-name warning for `code-review` is
  printed

#### Scenario: Opted out of the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, no `[rename]` key names **Entry** `mp/tdd`, and the user runs
  `skill-graft rename mp/tdd tdd`
- **THEN** `[rename]` holds `"mp/tdd" = "tdd"`, and the tree shows `mp/tdd` without `as`

#### Scenario: Back to the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, `[rename]` has `"mp/tdd" = "tdd"`, and the user runs
  `skill-graft rename mp/tdd mp-tdd`
- **THEN** `[rename]` no longer holds `mp/tdd`, and the tree shows `mp/tdd as mp-tdd`

### Requirement: Rename checks the skill

`rename` SHALL refuse a malformed **Skill ID**, an undeclared alias, or a **Skill** missing from its **Source**, writing
nothing. A **Skill** outside the **Hull** SHALL be renamed, with the unused-rename warning. A **Deployed name** that
clashes with another **Hull** **Skill** or the user's `reserved` SHALL be the usual error, writing nothing; one in the
shipped reserved list SHALL be written, with the usual warning.

#### Scenario: Unknown skill to rename

- **WHEN** **Source** `mp` has no **Skill** `nope` and the user runs `skill-graft rename mp/nope x`
- **THEN** it exits non-zero naming `mp/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Outside the hull

- **WHEN** `mp/notes` exists but is not in the **Hull**, and the user runs `skill-graft rename mp/notes n`
- **THEN** `[rename]` holds `"mp/notes" = "n"`, and the unused-rename warning names `mp/notes`

#### Scenario: Clash

- **WHEN** `mp/tdd` and `own/x` are in the **Hull** and the user runs `skill-graft rename own/x tdd`
- **THEN** it exits non-zero naming both **Skills**, and `skill-graft.toml` is unchanged

#### Scenario: User's reserved name

- **WHEN** `reserved = ["review"]`, `mp/check` is in the **Hull**, and the user runs
  `skill-graft rename mp/check review`
- **THEN** it exits non-zero naming `review`, and `skill-graft.toml` is unchanged

#### Scenario: Shipped reserved name

- **WHEN** `mp/check` is in the **Hull** and the user runs `skill-graft rename mp/check code-review`
- **THEN** `[rename]` holds `"mp/check" = "code-review"`, and the shipped reserved-name warning names it

### Requirement: Bind a name

`bind <alias>/<name> <target>` SHALL set `[bind]."<alias>/<name>"` to `<target>`, a **Skill ID**, or `false` when
`<target>` is the word `false`, replacing an existing value in place or appending a key, and SHALL append a `[bind]`
table at the end of the file when it is absent. A `<target>` equal to the current value, `false` included, SHALL be a
notice and change nothing, once the target is checked.

#### Scenario: New bind

- **WHEN** there is no `[bind]` table, **Entry** `mp/tdd` calls `/grilling`, and the user runs
  `skill-graft bind mp/grilling own/grill`
- **THEN** the file ends with a `[bind]` table holding `"mp/grilling" = "own/grill"`, and the tree shows `own/grill`
  under `mp/tdd`

#### Scenario: Bind to nothing

- **WHEN** **Entry** `mp/tdd` mentions `/tmp` and the user runs `skill-graft bind mp/tmp false`
- **THEN** `[bind]` holds `"mp/tmp" = false`, a TOML boolean, and the unmatched-**Reference** warning about `tmp`,
  printed before the bind, is gone

#### Scenario: Replaced

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"` with a trailing comment, and the user runs
  `skill-graft bind mp/grilling false`
- **THEN** the new file equals the old one with only that value replaced

#### Scenario: Already bound so

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"` and the user runs `skill-graft bind mp/grilling own/grill`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already bound to nothing

- **WHEN** `[bind]` has `"mp/tmp" = false` and the user runs `skill-graft bind mp/tmp false`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already bound to a skill gone upstream

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"`, `own` no longer has `grill`, and the user runs
  `skill-graft bind mp/grilling own/grill`
- **THEN** it exits non-zero naming `own/grill`, and `skill-graft.toml` keeps its bytes

### Requirement: Bind checks its key and target

`bind` SHALL refuse a malformed `<alias>/<name>` or an undeclared alias, and a `<target>` that is neither `false` nor a
**Skill ID** whose **Source** holds that **Skill**, writing nothing. `<name>` need not be a **Skill**. A **Bind** no
**Reference** uses SHALL be written, with the usual unused-bind warning.

#### Scenario: Unknown target

- **WHEN** **Source** `own` has no **Skill** `nope` and the user runs `skill-graft bind mp/grilling own/nope`
- **THEN** it exits non-zero naming `own/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Undeclared alias in the key

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft bind zz/grilling own/grill`
- **THEN** it exits non-zero naming the alias `zz`, and `skill-graft.toml` is unchanged

#### Scenario: Malformed target

- **WHEN** the user runs `skill-graft bind mp/grilling true`
- **THEN** it exits non-zero naming `true`, and `skill-graft.toml` is unchanged

#### Scenario: Unused bind

- **WHEN** no **Hull** **Skill** in `mp` mentions `grill` and the user runs `skill-graft bind mp/grill own/grill`
- **THEN** `[bind]` holds `"mp/grill" = "own/grill"`, and the unused-bind warning names `mp/grill`

### Requirement: A checked Skill ID reads only its Source

`rename` SHALL check its **Skill ID**, and `bind` its target **Skill ID**, by reading only that **Skill**'s **Source**,
fetching only a commit missing from the cache, before any other **Source** is read or its `ref` checked. A **Skill**
missing from its **Source** SHALL be reported before another **Source**'s missing `ref` or failed fetch. A no-op SHALL
read no other **Source**. A git **Source** of that **Skill** without a `ref` SHALL fail as `deploy` does, naming every
git **Source** without one.

#### Scenario: Unknown skill before another source

- **WHEN** git **Source** `other` has no `ref`, or one whose remote is unreachable, **Source** `mp` has no **Skill**
  `nope`, and the user runs `skill-graft rename mp/nope x`
- **THEN** it exits non-zero naming `mp/nope` and not `other`, and `skill-graft.toml` is unchanged

#### Scenario: Unknown target before another source

- **WHEN** git **Source** `other` has no `ref`, or one whose remote is unreachable, **Source** `own` has no **Skill**
  `nope`, and the user runs `skill-graft bind mp/grilling own/nope`
- **THEN** it exits non-zero naming `own/nope` and not `other`, and `skill-graft.toml` is unchanged

#### Scenario: Known skill, another source without a ref

- **WHEN** git **Source** `other` has no `ref`, `mp/notes` exists, and the user runs `skill-graft rename mp/notes n`
- **THEN** it exits non-zero naming `other` and `skill-graft update other`, and `skill-graft.toml` is unchanged

#### Scenario: No-op bind ignores other sources

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"`, `own` has `grill`, git **Source** `other` has no `ref`, and the
  user runs `skill-graft bind mp/grilling own/grill`
- **THEN** it exits 0 with the already-bound notice, and `skill-graft.toml` keeps its bytes

#### Scenario: No-op rename fetches no other source

- **WHEN** `mp/tdd` deploys as `tdd`, git **Source** `other`'s `ref` is not cached, and the user runs
  `skill-graft rename mp/tdd tdd`
- **THEN** it exits 0 with the already-deploys notice, fetches nothing for `other`, and `skill-graft.toml` keeps its
  bytes

#### Scenario: The skill's own source without a ref

- **WHEN** git **Sources** `mp` and `other` have no `ref`, and the user runs `skill-graft rename mp/tdd t`
- **THEN** it exits non-zero naming `mp`, `other` and `skill-graft update mp other`, and contacts no remote

### Requirement: Unbind a name

`unbind <alias>/<name>` SHALL delete the key from `[bind]`, leaving the table in place even if empty, so **References**
to `<name>` from that **Source** resolve by default again. A malformed key or an undeclared alias SHALL be refused as
`bind` refuses them, and a key not in `[bind]` SHALL be an error, both writing nothing.

#### Scenario: Unbound

- **WHEN** `[bind]` has only `"mp/grilling" = "own/grill"`, `mp` has `grilling`, **Entry** `mp/tdd` calls `/grilling`,
  and the user runs `skill-graft unbind mp/grilling`
- **THEN** `[bind]` is empty, and the tree shows `mp/grilling` under `mp/tdd`

#### Scenario: Not bound

- **WHEN** `[bind]` has no `"mp/grilling"` and the user runs `skill-graft unbind mp/grilling`
- **THEN** it exits non-zero naming `mp/grilling`, and `skill-graft.toml` is unchanged

#### Scenario: Unbind with an undeclared alias

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft unbind zz/grilling`
- **THEN** it exits non-zero naming the alias `zz`, not saying the key is not bound, and `skill-graft.toml` is unchanged

#### Scenario: Unbinding breaks resolution

- **WHEN** `[bind]` has `"mp/x" = "own/x"`, **Entry** `mp/tdd` calls `/x`, `mp` has no `x`, and both `own` and `other`
  have one, and the user runs `skill-graft unbind mp/x`
- **THEN** it exits non-zero, and `skill-graft.toml` and `skill-graft.lock` keep their bytes

### Requirement: Edit dry run writes nothing

`add`, `remove`, `rename`, `bind` and `unbind` with `--dry-run` SHALL check, resolve and print as without it, exiting
with the same code, but SHALL write neither `skill-graft.toml`, `skill-graft.lock`, `.apm/skills/`, `.gitattributes` nor
the cache, nor anything outside a temporary folder it removes before exiting, except the **Deployed diff** file
`--diff-file` names. It SHALL say `dry run: skill-graft.toml, skill-graft.lock and .apm/skills/ not written`, as its
last line on standard output. An edit that changes no value SHALL print only its notices, as without `--dry-run`, and no
`dry run:` line. A **Patch** failing in a dry run SHALL say, as `update --dry-run` does, that the upstream folder it
names was fetched into a temporary folder, and to run the same command without `--dry-run` to keep it.

#### Scenario: Dry run of an add

- **WHEN** the user runs `add mp/tdd --dry-run` and the edited config resolves
- **THEN** it prints the **Hull diff** and its `dry run:` line, and `skill-graft.toml`, `skill-graft.lock`,
  `.apm/skills/` and the cache folder are unchanged

#### Scenario: Dry run of a failing edit

- **WHEN** the user runs `add mp/notes --dry-run` and `mp/notes` calls `/x`, which matches several other **Sources** and
  no **Bind**
- **THEN** it exits non-zero as `add` would, and writes nothing

#### Scenario: Dry run with an edited copy

- **WHEN** `.apm/skills/tdd/SKILL.md` was edited and the user runs `bind mp/grilling cp/grilling --dry-run`
- **THEN** it exits 1 naming `.apm/skills/tdd`, as `bind` would

#### Scenario: Dry run with an uncached ref

- **WHEN** a git **Source**'s `ref` is not in the cache and the user runs `add mp/tdd --dry-run`
- **THEN** it fetches the commit into a temporary folder, and the cache folder is unchanged

#### Scenario: Dry run checking its target first

- **WHEN** `cp`'s `ref` is not in the cache and the user runs `bind mp/grilling cp/grilling --dry-run`
- **THEN** the cache folder is unchanged, though `bind` reads `cp` before resolving

#### Scenario: Dry run line last on standard output

- **WHEN** `mp/tdd` is already in the **Hull**, through another **Entry**, and the user runs `add mp/tdd --dry-run`
- **THEN** standard error holds the notice that `mp/tdd` was already in the **Hull**, and standard output ends with the
  `dry run:` line

#### Scenario: No-op dry run

- **WHEN** `mp/tdd` is already an **Entry** and the user runs `add mp/tdd --dry-run`
- **THEN** it prints only the notice that `mp/tdd` is already an **Entry**, and no `dry run:` line

#### Scenario: Patch failing in a dry run

- **WHEN** `mp`'s `ref` is not in the cache, a **Patch** of `mp/tdd` fails there, and the user runs
  `add mp/tdd --dry-run`
- **THEN** the error names `mp/tdd` and says to run `skill-graft add mp/tdd` without `--dry-run` to keep what it
  fetched, not to run `update`

### Requirement: Edit reports the hull diff

An edit with `--dry-run` or `--diff-file` SHALL print, before its tree, the **Hull diff** of the **Vendored copies**
against the **Hull** it would vendor, in `update`'s form: `hull (+ added, - removed, ~ changed):`, then `+`, `-` or `~`
and the **Skill ID** per **Skill**, sorted, each changed file under a `+` or `~` line as `update` names them; or
`hull unchanged`. A plain edit SHALL print as before. A **Skill** is matched to its copy through the lock's **Skill
IDs** and **Deployed names**, and a copy read only as an entry of `.apm/skills/`, or of the `.apm/skills.old/` a killed
run left when the next writing run would keep it; one the lock records without a copy, and every **Skill** with no lock,
is `+`, and a **Skill** is `-` only when it leaves the **Hull** and had a copy. A removed **Skill**'s ID, read from the
lock, SHALL be quoted as file paths are. Without `--diff-file`, when it marks a **Skill** `+` or `~`, it SHALL print
`review: skill-graft <command> <arguments> --dry-run --diff-file <file>`, each argument quoted for a POSIX shell, right
before its `dry run:` line.

#### Scenario: Skills joining

- **WHEN** `mp/tdd` calls `/grilling`, neither is in the **Hull**, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints `+ mp/grilling` and `+ mp/tdd`, each with its files as `(new, <n> bytes)`

#### Scenario: Text changed by a bind

- **WHEN** `mp/tdd` calls `/grilling`, and the user runs `bind mp/grilling cp/grilling --dry-run`, where `cp/grilling`
  deploys as `cp-grilling`
- **THEN** it prints `+ cp/grilling`, `- mp/grilling`, and `~ mp/tdd` naming its `SKILL.md`, whose reference is
  rewritten

#### Scenario: Renamed skill

- **WHEN** `mp/tdd` is in the **Hull** and the user runs `rename mp/tdd mp-tdd --dry-run`
- **THEN** it prints `~ mp/tdd`, not a `-` and a `+`

#### Scenario: First add

- **WHEN** the **Package** holds no lock and no `.apm/skills/`, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints every **Skill** of the **Hull** as `+`

#### Scenario: Hint

- **WHEN** the user runs `add mp/tdd --dry-run` without `--diff-file`, and `mp/tdd` joins the **Hull**
- **THEN** it prints `review: skill-graft add mp/tdd --dry-run --diff-file <file>` before its `dry run:` line

#### Scenario: Nothing changed

- **WHEN** `mp/tdd` is already in the **Hull**, through another **Entry**, and the user runs `add mp/tdd --dry-run`
- **THEN** it prints `hull unchanged` and no `review:` line

#### Scenario: Plain edit unchanged

- **WHEN** the user runs `add mp/tdd` without `--dry-run` or `--diff-file`
- **THEN** it prints what it printed before, and no **Hull diff**

#### Scenario: A lock pointing outside the copies

- **WHEN** the lock records `mp/tdd` with `deployed = "../../outside"` and no copy deployed under that name, and the
  user runs `add mp/notes --dry-run --diff-file review.diff`
- **THEN** it reads nothing outside `.apm/skills/`, and prints `mp/tdd` as `+`

#### Scenario: After a killed run

- **WHEN** a run was killed after swapping in new copies and before writing the lock, so `.apm/skills.old/` holds the
  copies the lock records, and the user runs `resolve --dry-run`
- **THEN** the **Hull diff** compares against the copies in `.apm/skills.old/`, not those in `.apm/skills/`

#### Scenario: A removed ID holding a control character

- **WHEN** the lock records a **Skill** whose ID holds a line feed and an escape character, and it leaves the **Hull**
- **THEN** its `-` line, and its `# -` line in the diff file, show the ID quoted, on one line

### Requirement: Edit deployed diff file

An edit with `--diff-file <file>` SHALL write the **Deployed diff** of its **Hull diff**'s `+` and `~` **Skills** to
`<file>`, refusing and ordering its writes as `update --diff-file` does: last in a dry run, before `skill-graft.toml`
otherwise, and removed if a later write fails. It SHALL remove an earlier file it wrote there once the edit is past its
no-op check, before resolving, and when it fails before its writes went through: an edit that changes no value leaves it
as it was, one that fails leaves none, and one that fails once written, such as on a closed standard output, keeps the
file of what it wrote. Its content SHALL follow `update`'s, its source lines naming each git **Source**'s `ref` as the
lock records it, quoted as file paths are, and as the command would vendor it, `old -> new` when they differ, only the
new one when the lock records none; each line of its marked tree SHALL be escaped as a line of the diff is; its header's
second line SHALL say it compares the **Vendored copies** against what the edited config would vendor.

#### Scenario: Diff file

- **WHEN** the user runs `add mp/tdd --dry-run --diff-file review.diff`, and `mp/tdd` and `mp/grilling` join the
  **Hull**
- **THEN** `review.diff` starts with the header and the marked **Hull**, then both **Skills**' files as added

#### Scenario: Removed skill

- **WHEN** the user runs `remove mp/tdd --dry-run --diff-file review.diff`, and `mp/tdd` leaves the **Hull**
- **THEN** `review.diff` holds the line `# - mp/tdd`, and none of `mp/tdd`'s text

#### Scenario: A file it did not write

- **WHEN** the user runs `add mp/tdd --dry-run --diff-file apm.yml` in a project-scope **Package**
- **THEN** it exits non-zero naming `apm.yml`, which keeps its bytes, before resolving

#### Scenario: A failed edit leaves no file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `add mp/notes --dry-run --diff-file review.diff`
  fails because `mp/notes` calls `/x`, which matches several other **Sources** and no **Bind**
- **THEN** `review.diff` no longer exists

#### Scenario: A refused edit leaves no file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `remove mp/typo --diff-file review.diff` fails
  because `mp/typo` is no **Entry**
- **THEN** `review.diff` no longer exists

#### Scenario: A ref the lock holds

- **WHEN** the lock records `mp`'s `ref` holding a line feed, or no `ref`, and the user runs
  `rename mp/tdd t --dry-run --diff-file review.diff`
- **THEN** `mp/tdd`'s source line names that `ref` quoted, on one line, or only the new `ref`

#### Scenario: A no-op edit keeps the file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, `mp/tdd` is already an **Entry**, and the user runs
  `add mp/tdd --diff-file review.diff`
- **THEN** it prints only its notice, and `review.diff` keeps its bytes

#### Scenario: Diff with a real edit

- **WHEN** the user runs `add mp/tdd --diff-file review.diff` and writing `skill-graft.lock` fails
- **THEN** it exits non-zero, `skill-graft.toml`, the lock and `.apm/skills/` keep their bytes, and `review.diff` does
  not exist

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- `/graft-vet`'s readers flag each line that speaks to them as a reviewer, telling them what to reply or flag or that
  the **Skill** is safe, as `permission`: the report file now shows that a **Skill** tries to talk its reviewer out of a
  **Flag**, where readers used to ignore such text without a word
- `/graft-vet`'s readers no longer flag a link named for you to read as `send`; a line that has the agent fetch it still
  is
- `/graft-vet`'s steering count no longer counts a place of the scan whose line the reader flagged in another category:
  a reader that disagrees on the category has not been talked into silence

### Fixed

- `skill-graft update` of a git **Source** without `branch`, whose remote holds tags but names no default branch, says
  so and suggests a `branch` key, where it said the remote had no commits yet

## [0.4.1] - 2026-11-06

### Added

- The `graft-vet` skill, `/graft-vet [skill-id…]`, installed as graft-check is and run only when you ask: it vets the
  **Skills** `skill-graft vet` vets. Hardened by graft-check's probe, it adds to the scan one reader per **Skill**,
  confined to that **Skill**'s folder and blind to the scan, that looks for intent rather than patterns. Code merges
  both into a report file you open, one line per **Flag** with who saw it, `scan`, `reader` or `both`; the agent sees
  only numbers, a steering count among them for where a reader stayed silent on what the scan saw. Unhardened, it is the
  scan alone, and reads no **Skill** text. It reports only, every report ending with fixed caveats, and names
  `skill-graft remove` for a flagged **Entry** at most
- `skill-graft vet --into <dir>` also writes each vetted **Skill**, as it scanned it, to `<dir>/<alias>/<name>/`, a
  **Skill** not yet added included, once every **Skill** is scanned. `<dir>` must be an empty folder outside any
  **Package**, **Source** and the cache, as for `deploy --into`; on any error it stays empty
- `skill-graft vet [skill-id…]`, a **Vet**: it points at the lines of each **Hull** **Skill**, as it would deploy, worth
  reading before trusting it, writing nothing. Named **Skill IDs** are vetted alone, one not yet added with what its
  `add` would bring in. One **Flag** per line, `<skill id> <file>:<line> <category> <owasp ids> <pattern>`, in eight
  categories (`read`, `write`, `send`, `run`, `privilege`, `persistence`, `permission`, `unreviewable`), its standard
  output never holding the text it matched. It never judges: it exits 0 whatever it flags, and no **Flag** is not a pass
- skill-graft is on PyPI, from 0.4.0 on: `uv tool install skill-graft==<version>`, or with pipx, pip or pipenv. Each
  file there is built from the signed release tag, and carries an attestation naming this repository's publish workflow
- In a project **Package**, every command that writes its `skill-graft.lock`, or would in its dry run, warns of each
  path **Source** the lock records as an absolute folder: one outside the project not written as `~/…`, or with a `..`
  in it. Other machines need that folder at the same place

### Changed

- `skill-graft vet` names the **Package** first on its standard error, `skill-graft: package: <package>`, as the
  commands that write do
- The README installs from PyPI first; installing from the repository at a signed tag stays, below it. Its links to
  other files of the repository work on the PyPI project page too, where those to the docs, CONTEXT.md and the logo name
  the release, so an older release's page leads to its own guides
- The README keeps a quickstart and the reference; the guides (adding and updating a **Source**, writing and redoing a
  **Patch**, a project **Package**, graft-check) are in `docs/howto.md`, and `docs/README.md` lists every doc. The
  README shows the skill-graft logo
- In a project **Package**, `skill-graft.lock` records a path **Source** written as `~/…` (`path = "~/skills"`) as
  written, empty and `.` segments dropped, so a committed lock reads the same on every machine. It recorded the absolute
  folder, which each teammate's `resolve` or `deploy` rewrote; a lock written before is rewritten once

### Fixed

- A **Skill** whose `name:` line holds a long run of whitespace no longer stalls every command that reads its
  **Source**: the name reads at once, as a name that is not one path segment; a long `apm.yml` line likewise
- `skill-graft vet` flags one- and two-digit world-writable `chmod` modes, such as `chmod 77` or `chmod 2`, as
  `privilege` **Flags**, as it did three- and four-digit ones
- graft-check's readers and patcher refuse to start when `$TMPDIR` is no folder, instead of taking any absolute path for
  a temporary one
- A `~user` path naming no user, in a path **Source** or in `[patches]`, ends with an error naming the path, not a
  traceback
- `update --dry-run` prints `nothing to apply` when the lock differs only in the folder a path **Source** is recorded
  at, not an `apply:` line
- Errors, warnings and notices write each unprintable character and **Hidden character** escaped (`\n`, `\x1b`), so a
  file name a **Skill**'s author chose, such as one holding a line break or a terminal escape, can neither forge an
  output line nor recolor the terminal; so does `update`'s `no previous hull to compare (…)`. git's error of several
  lines prints on one
- graft-check shows its agent no file name when it compares the throwaway deploy with the **Package**, nor in a
  **Patch** diff's error output; a diff that fails ends that fix, and the unhardened one deletes its patch file

## [0.4.0] - 2026-11-01

### Added

- graft-check checks the lock before it reads it, and ends the **Check** on a line skill-graft would not write, naming
  no value and advising to update skill-graft
- `add`, `remove`, `rename`, `bind`, `unbind` and `resolve` take `--dry-run` and `--diff-file <file>`, to see what they
  would vendor before they write it. `--dry-run` prints the **Hull diff** of the **Vendored copies** against what the
  command would vendor, each changed file named, and writes nothing; `--diff-file <file>` writes that text as deployed,
  the **Deployed diff**, to read in an editor. Before the first `add` every **Skill** shows as added

### Changed

- The README installs the latest release instead of `main`
- **BREAKING**: `build` is now `deploy`, its `--no-install` is `--no-apm-install`, and `update --diff <file>` is
  `update --diff-file <file>`; the old names exit 2. `deploy --into <dir>` is what `build --into <dir>` was. Options are
  no longer accepted abbreviated: `--dry` for `--dry-run` exits 2. Upgrade skill-graft first, then update its **Source**
  (`skill-graft update skill-graft` under `init`'s alias) and run `skill-graft deploy`: a graft-check vendored before
  this release runs `build --into` and ends with an error, and the new one runs `deploy --into`, which an older
  skill-graft refuses
- A **Deployed diff**'s first line names no command; a `review.diff` 0.3.0 wrote is still overwritten
- Each **Deployed diff**, `update --diff-file`'s too, opens after its header with the **Hull** as `tree` prints it, each
  **Skill** marked `+` added or `~` changed, then a `# - <skill id>` line per removed **Skill**
- In a hardened `/graft-check`, a reader's reply reaches the main agent only as a report filter shipped with the skill
  admits it: a report in the report shape, at most 100 findings and 200 uses, each value one line of printable ASCII of
  at most 200 characters, a character outside it shown as `?`. Any other reply runs its reader once more; a second one
  leaves its **Skill** with no report, `not in the report shape`, and none of either is shown
- A reader that fails shows one line of its error, in printable ASCII, at most 200 characters, as a failed patcher does
- A **Skill** under a folder named with anything but `A-Z a-z 0-9 . _ -`, or with only dots, is unusable: an **Entry**,
  a `[bind]` target, or a slash or `Skill(<name>)` **Reference** that needs it fails, naming the folder with every other
  byte written in octal (`my\040skills/tdd`). Elsewhere in its **Source** it blocks nothing. A path **Source** renames
  the folder; a git one needs a fork
- A git **Source**'s `subdirectory` takes those characters only: `subdirectory = "my skills"` is a config error
- The error for a **Skill** whose name is no path segment writes the name and its path with the same octal escapes
- `deploy` deploys only what `skill-graft.lock` records. It refuses, writing nothing and naming `skill-graft resolve`, a
  git **Source**'s **Skill** or a patched one whose hash differs from the lock's (the config or a **Patch** edited by
  hand, an edited cache export), any change to the **Hull**'s shape, and a missing lock or one of another `version`. The
  refusal names what differs: each **Skill**, edge (`own/tdd → own/notes (prose) added`), suggestion, deployed name or
  **Source**. A path **Source**'s **Skill** without **Patches** whose text changed is still deployed, and named:
  `<skill> changed in its path source since skill-graft.lock: deployed as is`. After editing `skill-graft.toml` or a
  **Patch** by hand, run `skill-graft resolve`, then `deploy`
- `resolve`, `update` and `add`, `remove`, `rename`, `bind`, `unbind` now write the **Vendored copies** in
  `.apm/skills/` too, together with the lock: on any failure both keep their bytes. Each also writes
  `.apm/skill-graft/.gitattributes` when the **Package** has none, so git keeps the committed copies' and **Patches**'
  line endings. `update --dry-run` still writes nothing
- No command overwrites an edited **Vendored copy**: each that vendors first checks `.apm/skills/` against the lock, and
  refuses, writing nothing, a copy whose hash differs (a stray file such as `.DS_Store` included), a folder the lock
  lists no **Skill** under, and a file directly in `.apm/skills/`, saying to move the edit into a **Patch** or delete
  the folder. A missing copy is vendored again. Without a lock it can read, the copies cannot be checked: the error says
  to delete `.apm/skills/`, then run `skill-graft resolve`
- `graft-check` runs `skill-graft resolve` after adding a **Patch** fix, and again after undoing one
- When APM fails after `init --project` registered the **Package**, `init` says to run `skill-graft resolve`, then
  `skill-graft deploy`
- skill-graft requires APM 0.35.0: install it with `uv tool install apm-cli==0.35.0`. A path **Source** inside or
  containing `~/agent-data/workflows`, or in project scope `agent-data/workflows` under the project root, where APM
  0.35.0's `grok-bot` target deploys skills, now gets the warning that it overlaps a folder where APM deploys skills
- Upgrading: a **Package** whose lock a `resolve` or an edit wrote after its last `build` holds copies older than its
  lock, which the first command refuses as edited. Check them, then delete `.apm/skills/` and run `skill-graft resolve`.
  A clone whose copies git already converted, as with `core.autocrlf`, is refused too: once `.gitattributes` is
  committed, delete them and check them out again (`git checkout -- .apm/skill-graft/.apm/skills`), or delete them and
  run `resolve`. A skill-graft upgrade that renders the lock or rewrites differently makes `deploy` refuse until
  `skill-graft resolve`

### Fixed

- The error line of a failed patcher no longer runs into the first line of its output when its error output ends without
  a line break
- Finding a skill's references no longer slows to minutes on a Markdown file with a long line holding many code spans
  each followed by `/`, such as `` `x`/a `` repeated: a long line takes no longer than the same text split into many
- With `PYTHONUNBUFFERED` set, `help`, `--help` and a command's `--help` into a pipe whose reader has closed it report
  the broken pipe and exit 1, as without it, instead of exiting 0
- `/graft-check` names the **Package**'s folder from the throwaway deploy's first line, so its closing advice compares
  the **Vendored copies** there, not a project folder above it, and no longer advises `skill-graft deploy` for nothing
- `/graft-check` writes a **Patch**'s diff after changing into its folder in a call of its own, which Claude Code no
  longer blocks as it blocked both in one command
- A hardened `/graft-check` starts its probe, readers and patcher through a script shipped with the skill, so Claude
  Code no longer blocks the command for changing folder and writing its output to files in one go. The script sets their
  confining flags itself and runs only in a temporary folder, so a permission rule allowing it allows no other `claude`
  run than a reader of the folders it is given or a patcher in a temporary folder

### Security

- The release tags are signed from this release on, with the SSH key the README names, and GitHub shows them as
  **Verified**. The README says how to check a tag and install the commit it names

## [0.3.0] - 2026-10-30

### Added

- The supported platforms are stated: Linux and macOS, and Windows through WSL. The README says so, and the package
  declares them as classifiers
- The git cache prunes itself: every command but `init` and `update --dry-run` removes, as it ends, each export no
  command has used for 30 days, and each leftover of a killed export or clone. No command removes a repository, and
  every **Ref** read stays in its repository, even after it vanished upstream. The README's new "Cache" section says
  where the cache is and when deleting it by hand loses a **Ref**
- A new clone of a git **Source** holds commits and trees only; an export fetches the files it writes, in one request,
  and a **Source** with `subdirectory` exports only that folder. A remote without partial clones gives a whole clone, as
  before; one refusing files asked by name has the repository fetched whole, once (git 2.36 or later). With git 2.44 or
  later, looking up what the cache holds never contacts the remote

### Changed

- The first export of a commit and `subdirectory` needs the remote, even when the commit is in the cache; an export
  removed as unused is exported again without it
- `update`'s **Hull diff** fetches the files of a cached current `ref` it lacks, so a lock written on another machine
  still gets its diff; when that fails, it says there is no previous **Hull** to compare, naming the fetch
- `update --dry-run` on a remote refusing files asked by name fails, naming the **Source** and saying to run `update`
  without `--dry-run`

### Fixed

- The error for an object missing from the cache no longer says to delete the repository, the one thing that can lose a
  **Ref** vanished upstream
- On native Windows, every command, `help`, `--help` and `--version` too, prints
  `skill-graft: native Windows is unsupported: run skill-graft in WSL` and exits 1, in place of a traceback ending in
  `No module named 'fcntl'`
- A **Patch** written with `diff -ruN` on macOS that deletes a file deletes it, as on Linux, with any folder that leaves
  empty; it left the file behind, empty, and one deleting `SKILL.md` was not refused. Any file a plain `diff` **Patch**
  leaves empty is deleted; a `git diff` **Patch** applies as git applies it

## [0.2.3] - 2026-10-29

### Added

- `tree --format mermaid` groups **Skills** by **Source** and draws **Entries** amber. A **Source** from GitHub or
  GitLab, and each of its **Skills**, link to the upstream tree at its **Ref**; the link is rebuilt from the
  repository's host and path, so nothing else from its URL, such as a token, reaches the diagram. A shared `--link`
  names those repositories

### Changed

- Every command prints its warnings last: after its output, its notices and APM's, with only its error line after them,
  and also when it fails. `build`'s no longer scroll away above APM's output, nor `update`'s above its **Hull diff**,
  and warnings about `skill-graft.toml` no longer come first
- `update --dry-run` with nothing to apply, no **Ref** moving and the lock it would write recording what
  `skill-graft.lock` records, says `nothing to apply` in place of its `apply:` line. Moving no **Ref**, its prose
  suggestion line says to run `resolve`, not to update first
- `--expect` names its value `<hull-digest>`, after the **Hull digest** it takes: `update --help` shows
  `--expect hull-digest`, and a mismatch says `its hull digest is …`
- `rename` and `bind` look up the **Skill** they are given in its own **Source** only: a missing **Skill** is reported
  before another **Source**'s missing **Ref** or failed fetch, and a `rename` or `bind` that changes nothing no longer
  needs any other **Source**. A `bind` target that is no **Skill ID** is refused as `bind: '<target>' is not …`, without
  naming the key

### Fixed

- When writing `skill-graft.lock` fails after `update` moved a **Ref**, or Ctrl-C interrupts it, `skill-graft.toml` is
  restored; so is it when Ctrl-C interrupts an edit's lock write. A restore that fails too is named, and the original
  error is the one reported
- Without APM, `init` creates nothing and says to install APM and run `init` again, instead of leaving a **Package**
  that a second `init` refuses with no way forward
- Refusing an existing **Package** that APM does not list, `init` gives the `apm install` command that registers it
- The `apm install` commands `init` suggests, and the one named when APM fails, are shell-quoted
- Into a pipe its reader has already closed, such as `skill-graft tree | head -1`, a command prints its warnings, then
  its error line, and exits 1, with no `Exception ignored … BrokenPipeError` from Python and no exit 120; so do `help`,
  `--version` and `--help`. A command started with standard output closed no longer fails with a traceback

## [0.2.2] - 2026-10-26

### Added

- `update --diff <file>` writes the **Deployed diff**: each changed or added **Skill**'s text as deployed, **Patches**
  and **Renames** applied, as a unified diff to read in an editor, never printed. Every control, format and separator
  character, and every **Hidden character**, is escaped, so no line hides or passes for another. It writes only a new
  `*.diff` file or one it wrote before, never inside an `.apm` folder or a **Skill**'s folder
- `update --expect <digest>` updates only to the **Hull** with that **Hull digest**: a dry run with `--diff` ends with
  the `apply:` line to run, and a push, a path **Source**'s edit, a **Patch** or a **Rename** since then makes it
  refuse, writing nothing

### Changed

- `update` names each changed file under each changed or added **Skill**, with its sizes and executable bit, never its
  text; a dry run without `--diff` ends with the `review:` command to run
- `update` names each **Skill** edited since `skill-graft.lock` was written, whose earlier text no diff can show, and
  then prints no `apply:` line
- An old **Ref** missing from the cache is named as such, with its likely causes, instead of "not cached"

### Fixed

- With several git **Sources** without a `ref`, every command names them all and suggests one `skill-graft update` that
  works: `update a` suggests `skill-graft update a b`, keeping `--dry-run` and `--diff` (and turning `--expect` into
  `--dry-run`), instead of hints sending the user from `a` to `b` and back

## [0.2.1] - 2026-10-24

### Added

- `skill-graft --version` prints the installed version; installed from git, also the commit, and the branch or tag if
  one was named: `skill-graft 0.2.0 (main @ e294a0e)`; without a readable installation, `skill-graft unknown`
- An OWASP Top 10 section in `docs/security.md`: how skill-graft meets each risk of the LLM and agentic lists, what is
  out of scope (judging whether a **Skill** is malicious), and future work
- A `[check]` table in `skill-graft.toml` for the limits of a hardened `/graft-check`: `reader-turns` (30),
  `reader-budget-usd` (1.0), `patcher-turns` (10), `patcher-budget-usd` (0.5) and `readers-at-once` (4), each written in
  plain decimal digits; any other form fails like any bad key

### Changed

- `/graft-check` is hardened in any harness with a working Claude Code, not only in Claude Code: before reading any
  **Skill** text it runs one probe reader, and outside Claude Code it first asks to use your Claude Code account. A
  failed probe makes the **Check** unhardened, naming the probe's error and, when not logged in, advising
  `claude auth login`
- In a hardened `/graft-check`, each reader and the patcher stop at a cap on their turns and their spend, and at most
  `readers-at-once` readers run at once, in batches. A reader that stops leaves its **Skill** with no report; a patcher
  that stops ends that fix
- The patcher's reply no longer reaches the main agent. A failed patcher shows one line of its error, in printable
  ASCII, at most 200 characters
- The summary of a proposed **Patch** gives counts only (`files: 1, lines: +2 -1, binary: 0`), never the patcher's file
  names. A binary file, or a file name holding a control character, ends that fix

## [0.2.0] - 2026-10-23

### Added

- On Claude Code, `/graft-check` reads **Skill** text only through headless readers, `claude -p --restricted` limited to
  `Read`, `Grep` and `Glob`, without MCP servers and confined to that **Skill**'s folders; its own session sees only CLI
  output and the readers' reports. A **Patch** it proposes is written by a patcher confined to a temporary folder, and
  you read its diff before it enters the **Package**. Elsewhere, or with a `claude` lacking those flags, it says the
  **Check** is unhardened and why, and reads only on your yes
- A warning for invisible characters common as copy-paste debris (zero-width, soft hyphen, bidi marks), once per file
  with its first line and count
- `docs/security.md` and a Security section in the README: what APM and skill-graft block, what the **Check** enforces
  on Claude Code, running it in Claude Code's sandbox, and the residual risks

### Changed

- **BREAKING**: resolution fails when a **Hull** **Skill** holds a **Hidden character**, in its **Upstream** text, a
  file or folder name, or the lines its **Patches** add, naming each file, line and character class; one run reports
  them all. `resolve`, `build` (`--into` too), `update` and the editing commands write nothing; `why` and `tree` print
  the **Hull**, then fail. Such a **Hull**'s `build` already failed in APM; now `resolve` fails too
- **BREAKING**: a Markdown file of a **Hull** **Skill** that is not UTF-8, **Upstream** or as patched, fails resolution
  instead of being skipped with a warning; so does any file of it that cannot be read

### Security

- A `SKILL.md` that a git **Source** links outside its **Skill**, or that is not a regular file (a FIFO or device, or a
  link to one), is no longer read, so a **Source** can neither make skill-graft read a local file nor hang it. Such a
  **Skill**'s name is unreadable: an **Entry** or **Reference** naming its folder fails, naming the `SKILL.md`, never
  what it links to; other **Entries** never see it

## [0.1.0] - 2026-10-22

### Added

- `skill-graft init` creates the package, `~/.apm/skill-graft/`, with a commented `skill-graft.toml`, and registers it
  with APM. `init --project` creates one in the project instead, `.apm/skill-graft/`, registered in the project's
  `apm.yml`; every command then acts on the nearest package above the working folder, and on the user scope's when there
  is none
- `skill-graft build` vendors the hull into the package's `.apm/skills/` and deploys it through APM into Claude Code,
  opencode and the other harnesses APM supports; `--no-install` stops before APM, and `--into <dir>` writes the skills
  and the lock into an empty folder instead, leaving the package and APM untouched
- Sources: local folders (`path`) and git repositories (`git`, with an optional `branch`), each git source read at the
  commit its `ref` names and cached outside the package. `subdirectory` reads only one folder of a repository, as if it
  were its root
- `skill-graft update [source…] [--dry-run]` moves each git source's `ref` to its branch tip, only if the hull still
  resolves and every patch still applies there, and prints which skills that adds, removes or changes
- The hull: the entries plus every skill they reach through slash references (`/grilling`) and Skill tool references
  (`Skill(grilling)`, or a sentence telling the reader to call the Skill tool with `grilling`), found in every Markdown
  file of a skill. A reference resolves in its own source first, else in exactly one other; one matching no skill is a
  warning. Prose references to a skill outside the hull become suggestions to `add`
- `skill-graft resolve` computes the hull, writes `skill-graft.lock` and prints the hull as a tree, followed by the
  suggestions
- `[bind]`, and `skill-graft bind` and `unbind`: fix which skill a name from one source resolves to, or make it no
  reference at all with `false`
- `[rename]` and a source's `prefix` set a skill's deployed name, carried into its folder, its `name:` and every
  reference to it, prose included; `skill-graft rename` sets or undoes a rename. Deployed names must be unique across
  the hull; a name a harness already uses, such as `code-review`, is a warning, and one in your own `reserved` list an
  error
- `[patches]`: unified diffs applied to a skill's upstream text before its references are read, so a patch can change
  what a skill calls. A patch that fails names each failing hunk, and nothing is written
- `skill-graft tree [--format text|mermaid] [--link]` and `skill-graft why <skill>` explain the hull without writing
  anything: the whole tree, as text, Mermaid or a mermaid.live link, or the paths from the entries to one skill and its
  upstream folder
- `skill-graft add` and `remove` change `entries`, keeping the file's comments, once the result resolves
- `skill-graft help [command]`, and `--help` on every command
- The `graft-check` skill, in this repository's `skills/`: run as `/graft-check`, it has an agent read a built package
  for missed, false or misdirected references, wrong rewrites and links vendoring broke, and proposes `add`, `bind`,
  `unbind` or a patch for each, applied only once you accept

[0.1.0]: https://github.com/remigius42/skill-graft/releases/tag/v0.1.0
[0.2.0]: https://github.com/remigius42/skill-graft/compare/v0.1.0...v0.2.0
[0.2.1]: https://github.com/remigius42/skill-graft/compare/v0.2.0...v0.2.1
[0.2.2]: https://github.com/remigius42/skill-graft/compare/v0.2.1...v0.2.2
[0.2.3]: https://github.com/remigius42/skill-graft/compare/v0.2.2...v0.2.3
[0.3.0]: https://github.com/remigius42/skill-graft/compare/v0.2.3...v0.3.0
[0.4.0]: https://github.com/remigius42/skill-graft/compare/v0.3.0...v0.4.0
[0.4.1]: https://github.com/remigius42/skill-graft/compare/v0.4.0...v0.4.1
[unreleased]: https://github.com/remigius42/skill-graft/compare/v0.4.1...HEAD

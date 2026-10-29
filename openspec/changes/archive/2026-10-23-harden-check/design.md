# Design

## Context

See proposal.md for why, ADR 0007 for the decision. What the change builds on:

- `hull.walk` visits each **Hull** **Skill** once: `files.check_files`, then `patch.apply` into a copy under the walk's
  temporary folder, then `references.scan`. Patch failures are collected in `failed` so the walk goes on, and raised
  together as `patch.PatchError`, with any other error that stopped the walk after them.
- `references.scan` reads only Markdown and skips a file that is not UTF-8, with a warning.
- APM 0.33.0 blocks an install on the same critical classes (`security/content_scanner.py`); `build --into` never runs
  APM, so today nothing checks what the **Check** reads.
- The skill today runs one in-session subagent per **Skill**, with every tool the session has, and its main agent reads
  **Upstream** text for wrong targets and edits files to write **Patches**.
- `claude --help` (Claude Code at the time of writing) lists `-p`, `--restricted` (no Bash, other code runners or
  WebFetch unless `--tools` names them; user, project and local settings ignored; file tools confined to the working
  folder and `--add-dir`), `--tools`, `--agents <file>` with `-p`, `--agent` and `--strict-mcp-config`.
- A spike on Claude Code 2.1.309, with a synthetic **Skill** telling its reader to run `touch` and `curl`, write a
  marker, read a file outside its folder and use WebFetch, confirmed:
  - The reader command below starts with tools `Read`, `Grep`, `Glob` and no MCP server; the definition's `tools` alone,
    without `--tools`, gives the same list.
  - `Read`, `Grep` and `Glob` outside the working folder and `--add-dir` are refused ("is outside …; --restricted
    confines the file tools to the working directory"); nothing was written, run or fetched, and the secret did not
    reach the output.
  - Auth works under `--restricted` from the user's own login. A reader costs about 0.06 USD.
  - With `--tools Read,Edit,Write`, `Write` outside the working folder is refused; inside it, `-p` refuses it too unless
    `--permission-mode acceptEdits`.
  - `--tools` and `--add-dir` take any number of values, so a prompt after them is swallowed: the prompt goes on stdin.
  - `CLAUDECODE=1` in Claude Code's Bash; `${CLAUDE_SKILL_DIR}` in a `SKILL.md` expands to the skill's folder.

## Goals / Non-Goals

**Goals:**

- On Claude Code, no agent with a shell, writes outside a temporary folder, or network ever holds **Skill** text.
- No **Hidden character** reaches any agent through a **Hull** **Skill**, in any harness.

**Non-Goals:**

- Detecting visible prompt injection in the text; the readers are confined, not trusted.
- Hardening the **Check** on other harnesses, or wrapping it in an OS sandbox.
- Scanning **Skills** outside the **Hull**, or `skill-graft.toml` itself.

## Decisions

- **A pipeline module, `hidden.py`, scanned in the walk.** `scan(folder) -> (found, warnings)` checks the name of every
  entry of `files.skill_entries` and the text of every file. Markdown must decode strictly as UTF-8, as its
  **References** are read. Any other file: a UTF-32 byte order mark, then a UTF-16 one (UTF-32LE's starts with
  UTF-16LE's), picks that codec; else strict UTF-8, NULs being valid UTF-8, so a NUL cannot switch the scan off; else,
  without a NUL, UTF-8 with `errors="replace"`, so one bad byte hides nothing; else binary, skipped. Skipping binaries
  is needed: scanning random bytes leniently, a 3-byte bidi sequence turns up by chance about once per 2 MB. The walk
  scans the **Upstream** folder, then the `+` lines of each patch file (context lines repeat **Upstream** ones, which
  would report twice), then in the patched copy every name the **Upstream** lacks (git writes non-ASCII paths in octal
  escapes, so a patch header hides them), and every Markdown file a patch changed, which must stay UTF-8. No patch
  writes a file the `+` lines do not show: the config refuses a `GIT binary patch` block. Found characters, and Markdown
  that is not UTF-8, are collected like `failed`, and the walk goes on. Alternative: scan in `vendor`. Rejected:
  `resolve`, `why`, `tree` and the editing commands never vendor, and the **Check** reads **Upstream** folders, not
  vendored ones.

- **`why` and `tree` print before failing.** The walk's collected-failures error carries the **Hull** as walked when it
  failed only on **Hidden characters** or Markdown that is not UTF-8, so these two print it, then the error, exit 1; the
  writing commands raise it as before. A patch failure still stops them, as the **Hull** past it is unknown.

- **One error for patch failures and hidden characters.** `PatchError` becomes the walk's collected-failures error,
  holding both lists, so one run reports both in a fixed order (patches, hidden characters, then the error that stopped
  the walk) and the unused-key warnings stay left out. Each list gets its own header ("patches do not apply:", "hidden
  characters:"), printed only when it has entries. Its callers in `commands/update.py` follow: `_fetch_hint` carries the
  hidden list through when it rebuilds the error, and `_previous` says which of the two failed at the current refs.
  Alternative: a second error class raised after `PatchError`. Rejected: one would hide the other.

- **The class table is APM's critical and warning sets,** copied as ranges with a comment naming APM's file and version,
  since `apm_cli` is no API. Lone surrogates are left out: strict UTF-8 decoding refuses them, and lenient decoding
  replaces them.

- **Readers: `claude -p` with the reader's definition from the skill's folder,** `${CLAUDE_SKILL_DIR}`, run from a new
  empty `mktemp -d` folder, the prompt on stdin:

  ```sh
  claude -p --restricted --strict-mcp-config --tools Read,Grep,Glob \
    --agents <skill folder>/reader.json --agent reader \
    --add-dir <upstream> --add-dir <vendored copy> [--add-dir <target upstream>…] < <prompt file>
  ```

  The reader's working folder also holds a copy of that **Skill**'s own patch files, made with `cp`, so it sees no other
  **Skill**'s patches and no folder a patch path happens to sit in. Its targets' **Upstream** folders let it judge a
  wrong target against what the target says; they are as untrusted, and as confined. The Kinds section moves from
  `SKILL.md` into the reader's prompt. The main agent passes in the prompt only the **Skill ID**, paths, the tree's
  targets and written names for that **Skill**, and that **Source**'s `[bind]` keys. `--tools` and the definition's
  `tools` both say `Read, Grep, Glob`, so either alone suffices. Alternative: an agent definition deployed through APM
  (ADR 0007).

- **Readers report every use of each candidate name.** Besides findings, a reader lists each use of a name the main
  agent gave it, with its verdict (means that target, or not). Before proposing a **Bind** for `<alias>/<name>`, the
  main agent runs a use-only reader, asked about that name alone, on every **Hull** **Skill** of `<alias>` that has no
  use list for that name yet, the user's scope notwithstanding, and proposes the **Bind** only when every use is wrong.
  The source-wide search needs no text in the main agent. A finding quotes its **Upstream** line in `text`, and for a
  finding the build caused, such as a rewrite or a broken link, the built line in `vendored`.

- **Patcher: the same command shape,** `--tools Read,Edit,Write`, `--permission-mode acceptEdits`, `patcher.json`, run
  in its own `mktemp -d` folder holding only `edited/`, no `--add-dir`. The main agent builds `base/` in a second
  `mktemp -d` folder the patcher cannot reach, with `cp -rL` and `git apply`, which bring no text into its context, and
  copies it to `edited/`. After the patcher, it runs `diff -ruN base/ edited/` into a file beside `base/`, with per-file
  counts of added and removed lines, leaving out the `---` and `+++` headers, and gives the user the path. A hijacked
  patcher can only shape `edited/`, which is what the user reviews.

- **Detecting Claude Code.** The skill is hardened when `CLAUDECODE` is set, `claude` is on `PATH`, and `claude --help`
  lists `--restricted`, `--strict-mcp-config`, `--tools` and `--agents`; an exit code proves nothing, since `--help`
  exits 0 after unknown flags too. Otherwise it asks (spec: Unhardened only on the user's yes). The unhardened path
  keeps today's in-session subagents and **Patch** recipe.

- **Fix arguments checked by the main agent,** against the lock, `tree` and `[sources]`, each side of the slash matching
  `config.NAME`, `[A-Za-z0-9][A-Za-z0-9._-]*`, single-quoted in every command. Prompt-level, listed as residual risk.

## Risks / Trade-offs

- \[A later Claude Code changes what `--restricted` confines\] → the `injected` eval scenario catches it when the skill
  changes; `docs/security.md` names the version the spike ran on.
- \[A report's quoted `text`, or its `vendored` line, carries an injection into the main agent\] → each one line, at
  most 200 characters, shown, never followed; the user accepts each fix. Documented as residual.
- [A non-Markdown file with a NUL byte that is not UTF-8, such as BOM-less UTF-16 text, is skipped as binary] → no
  Markdown can be, since Markdown must be strictly UTF-8; documented as residual.
- [The sandbox blocks the readers] → each reader is a `claude` process needing the API's network and writes under
  `~/.claude`; `docs/security.md` says what the sandbox must allow for the **Check**, or to run it without.
- \[Each reader is a separate `claude` process\] → more start-up time and tokens than a subagent; the **Check** is rare
  and user-invoked.
- \[`--restricted` ignores the user's settings, so a model or MCP choice there does not apply\] → intended: no setting
  can widen the reader.
- \[A legitimate **Skill** with RTL text uses bidi isolates\] → it fails, as APM's install already fails it; the fix is
  upstream, or leaving the **Skill** out of the **Hull**.

## Migration Plan

A **Hull** that resolved before can fail now: on a **Hidden character**, whose `build` already failed in APM, and on a
Markdown file that is not UTF-8, which only warned. Both are **BREAKING**; the `CHANGELOG` entry says so. The skill's
new files ship with it; users get them with `skill-graft update` on the **Source** and a `build`.

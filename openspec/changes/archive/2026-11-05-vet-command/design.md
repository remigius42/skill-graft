# Design

## Context

`tree` and `why` (`commands/explain.py`) already compute the **Hull** without writing anything, through
`compute.compute_hull`. Each **Skill** as it would deploy is `deployed.deployed_files(hull.skills[s], rewrites[s])`,
with `rewrites = rename.rewrites(hull)`, as `review.py` builds the Deployed diff. `hidden.decode_as` reads any file as
resolution does. `commands/edit.py` holds `_reach`, what some **Skills** reach over slash and Skill tool edges. The
decisions behind the **Vet** are in ADR 0010; the grilling that settled them is summed up in the proposal.

## Goals / Non-Goals

**Goals:**

- One deterministic scan, a pure function from a **Skill**'s deployed files to **Flags**, testable without a **Source**.
- Output the `graft-vet` skill's main agent can read whole: no **Skill** text but sanitized file names.

**Non-Goals:**

- Parsing scripts or shells: patterns are line-wise regular expressions and small line-wise checks, approximate by
  design.
- Running anything a **Skill** ships.
- A diff mode, a JSON format, a summary per category: the `graft-vet` change merges and presents.

## Decisions

### Two modules, on two layers

`pipeline/vet.py` holds the categories, the OWASP table, the named patterns and `scan(view) -> list[Flag]`, over one
**Skill**'s `deployed.View`, whose `SKILL.md` gives the front matter. `commands/vet.py` computes the **Hull**, picks the
**Skills** to vet, scans each, prints. `explain.py` would have fit ("views of the hull"), but it is already 432 lines
and the scan is no view of the **Hull**'s shape. `Flag` is a frozen dataclass: file, line, pattern; its category is the
pattern name's prefix and the OWASP IDs come from the table by category when printed, so no **Flag** can carry others.
The **Skill ID** is the command's to add: `scan` sees one **Skill**'s files only. `commands/vet.py` imports the module
as `patterns`, its own function being `vet`.

### Which Skills, with one Hull computation

With **Skill IDs**, each is checked as `rename` and `bind` check theirs (`compute.known`, its error naming `vet`; `add`
finds an unknown one only when it resolves, naming it an entry), then the **Hull** is computed from the config with
those outside it appended to `entries` (`dataclasses.replace`), never written. What their `add` brings in is the widened
**Hull**'s **Skills** that the original **Entries** do not reach: `reach(hull, config.entries)` over the widened
**Hull** gives the original one, since edges do not depend on the entries (as `_reach`'s docstring already argues).
`_reach` moves to `pipeline/hull.py` as `reach`, `edit.py` calling it there: a sibling import from `commands/edit.py`
would bind two unrelated commands. Alternative: compute both **Hulls**, twice the reading for the same answer. The
**Skills** vetted print in **Hull** order: those already in the **Hull** in its order, the **Entries** then `reach`'s,
both walks being breadth-first from the **Entries**; then those their `add` brings in, in the widened **Hull**'s order.
A **Skill** named that is in the **Hull** but no **Entry** is appended to `entries` too, so the widened **Hull**'s order
alone would move it ahead.

### Patterns are named, line-wise, case-insensitive

Each pattern is a name, `<category>.<what>`, and a line-wise regular expression or, where a regex would backtrack, a
check function; the category is the name's prefix, e.g. `run.pipe-to-shell`, `send.url`, `privilege.sudo`,
`permission.no-ask`. A line yields one **Flag** per matching pattern, so one line can carry several categories (the
pipe-to-shell scenario). Starting list, tuned in tests:

| Category       | Patterns                                                                                                                                                                                                                                                                                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `read`         | `outside-path`, `secret-store` (`.ssh`, `.aws`, `.gnupg`, `.env`, `.netrc`, `.npmrc`, `.pypirc`, `id_rsa`, `id_ed25519`, keychain, `credentials`)                                                                                                                                                                                                                                     |
| `write`        | `outside-path` on a line with `>`, `>>`, `tee`, `cp`, `mv`, `install`, `ln`, `mkdir`, `touch`, `sed -i`, or `write`, `save`, `append` (words)                                                                                                                                                                                                                                         |
| `send`         | `url` (a scheme and `://`), `network-tool` (`curl`, `wget`, `nc`, `ncat`, `scp`, `rsync` to a host, `ssh`, `Invoke-WebRequest`), `network-call` (`requests.`, `urllib`, `httpx`, `fetch(`, `socket`), `web-tool` (`WebFetch`, `WebSearch`), `push` (`git push`, `gh pr create`, `gh gist`), `mail`                                                                                    |
| `run`          | `shell-block` (a fence opening `sh`, `bash`, `zsh`, `shell`, `console`, `powershell`), `pipe-to-shell` (or an interpreter), `eval` (`eval`, `exec(`, `os.system`, `subprocess`, `sh -c`, `bash -c`), `destructive` (`rm -rf`, `rm -r -f`, `dd if=`, `mkfs`, `shred`, a fork bomb), `executable` (the bit, line 0), `shebang` (line 1)                                                 |
| `privilege`    | `sudo`, `su`, `doas`, `pkexec`, `runas`, `world-writable` (`chmod 777`, `o+w`, `a+w`), `setuid` (`u+s`, `g+s`, a 4- or 2-prefixed mode), `chown-root`                                                                                                                                                                                                                                 |
| `persistence`  | `agent-config` (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/`, `.cursor/`, `.codex/`, `settings.json`, `.mcp.json`), `hooks` (a `hooks:` front matter key, `.git/hooks`, `hooks` in agent settings), `shell-rc` (`.bashrc`, `.zshrc`, `.profile`, `.bash_profile`, `config.fish`), `scheduler` (`crontab`, `cron.d`, `systemctl enable`, `launchctl`, `LaunchAgents`, `schtasks`) |
| `permission`   | `tool-grant` (an `allowed-tools:` front matter key in `SKILL.md`), `skip-prompts` (`--dangerously-skip-permissions`, `bypassPermissions`, `--permission-mode`, `--yolo`), `no-ask` ("without asking", "do not ask", "don't tell the user", "silently", "quietly", "do not mention")                                                                                                   |
| `unreviewable` | `binary`, `encoding` (decodes, but not as strict UTF-8; line 0), `long-line` (over 1000 characters), `encoded-blob` (200 or more base64 or hexadecimal characters in a row)                                                                                                                                                                                                           |

Front matter is the block between a first line `---`, after a byte order mark if any, as `references.front_matter` reads
it, and the next, in `SKILL.md` only; only its top-level keys count, so `allowed-tools` nested under `metadata:` is
none. Commands match as words not part of a dotted or hyphenated name: `subprocess` does not flag `su`, nor `.ssh` or
`ssh-keygen` `ssh`, while `/usr/bin/ssh` does. `send.mail` is `sendmail`, `mail`, `mailx`, `smtplib` or `smtp`;
`run.pipe-to-shell` a pipe into `sh`, `bash`, `zsh`, `dash`, `ksh`, `fish`, `pwsh`, `powershell` or `iex`, or an
interpreter reading its stdin, `python`, `python2`, `python3`, `node`, `perl` or `ruby`, as a whole word, `sudo` allowed
between; `run.destructive` an `rm` whose run of options holds `r`, `R` or `--recursive` and `f` or `--force`, bundled or
not; `privilege.setuid` and `privilege.world-writable` read each `chmod`'s mode, its first argument not an option (long
ones too), a quote or backtick around it and the punctuation ending a sentence dropped: octal, leading zeros dropped, or
symbolic clauses `[ugoa]*[+=]...`. setuid is a four-digit mode whose first digit holds the 4 or 2 bit (2 to 7), or an
`s` for `u`, `g`, `a` or no one named (`+s`); world-writable a last digit holding the 2 bit (2, 3, 6, 7), or a `w` for
`o` or `a` (`+w` alone obeys the umask, so is none); `privilege.chown-root` `root` as `chown`'s first argument not an
option; `unreviewable.encoded-blob` 200 characters of `[A-Za-z0-9+/]` in a row, hexadecimal being a subset;
`unreviewable.long-line` a line of 1001 characters or more. A pattern starts only where a run starts, or scans the line
from its start once (`rsync`, a lookahead from the line's start), so no crafted line takes quadratic time: a skill must
not stall the scan meant to vet it. Every pattern has a test that it flags its line and one that it leaves a near miss
alone.

### Paths outside the project

One regex finds path-like tokens, split at white space, quotes, brackets, `<>|;,=`; a token is outside when it starts
with `/` and a folder (`/a/`: a lone `/grilling` is a slash command), with `~` alone, `~/` or `~user/`, with `$HOME` or
`${HOME}` alone or before `/`, or when its `..` parts outnumber the parts before them (`posixpath.normpath`'s first part
`..`, so an ellipsis is none). A URL's path is no path: tokens inside a `scheme://` are skipped. Write vs read is
decided per line by the write markers above, `>` counting unless after `-`, `=`, `<` or `>`. A redirection that discards
output (`2>/dev/null`) or joins two streams (`2>&1`) is dropped first: no write, and `/dev/null` no path.

### Files

Each file of the view is decoded by `hidden.decode_as(data, markdown, "replace")`: `None` is `unreviewable.binary` at
line 0, an encoding other than strict UTF-8 is `unreviewable.encoding` at line 0 and its text is still scanned. Lines
split on `\n`, numbered from 1, as `hidden.py` numbers them. The executable bit comes from the view.

### Output

Lines are `" ".join([skill, f"{name}:{line}", category, ",".join(ids), pattern])`, where `name` maps each character
outside `!`..`~` to `?`: stricter than `text.show`, as the line is split on spaces by the `graft-vet` filter. The
**Skill ID** needs no mapping, its parts matching `[A-Za-z0-9._-]`. In **Hull** order, then as `scan` returns them, each
once: by the file's path bytes (the view's order), line, pattern. The closing notice goes through `errors.notice`, so it
precedes the warnings:
`<n> flags in <m> skills: a flag is not a fault, and no flag is not a pass; read each line flagged, and the rest`, `<m>`
counting the **Skills** vetted. As `tree` and `why`, `vet` prints no package line, so its errors are `resolve`'s without
it.

## Risks / Trade-offs

- \[Patterns are easy to evade: `s"u"do`, a variable, base64\] → the `unreviewable.encoded-blob` pattern catches some;
  the notice and `docs/security.md` say a missing **Flag** proves nothing; the `graft-vet` readers look for intent.
- \[Noise: every documentation URL is a `send` **Flag**\] → accepted: a **Vet** that hides **Flags** to look tidy would
  be a verdict; the pattern name lets a reader skim `send.url` apart from `send.network-call`.
- \[A **Skill** in the repository itself, `graft-check`, flags heavily\] → expected; its tests run on synthetic
  **Skills**, never on it.
- \[The pattern list changes between versions, so **Flags** do too\] → the CHANGELOG names pattern changes.

## Migration Plan

None: a new command, no change to the config, the lock or the vendored bytes.

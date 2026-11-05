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

- Parsing scripts or shells: patterns are line-wise regular expressions, approximate by design.
- Running anything a **Skill** ships.
- A diff mode, a JSON format, a summary per category: the `graft-vet` change merges and presents.

## Decisions

### Two modules, on two layers

`pipeline/vet.py` holds the categories, the OWASP table, the named patterns and `scan(view, skill_md) -> list[Flag]`,
over one **Skill**'s `deployed.View`. `commands/vet.py` computes the **Hull**, picks the **Skills** to vet, scans each,
prints. `explain.py` would have fit ("views of the hull"), but it is already 432 lines and the scan is no view of the
**Hull**'s shape. `Flag` is a frozen dataclass: skill, file, line, category, pattern; the OWASP IDs come from the table
by category when printed, so no **Flag** can carry others.

### Which Skills, with one Hull computation

With **Skill IDs**, each is checked as `add` checks it (`compute.known`), then the **Hull** is computed from the config
with those outside it appended to `entries` (`dataclasses.replace`), never written. What their `add` brings in is the
widened **Hull**'s **Skills** that the original **Entries** do not reach: `reach(hull, config.entries)` over the widened
**Hull** gives the original one, since edges do not depend on the entries (as `_reach`'s docstring already argues).
`_reach` moves to `pipeline/hull.py` as `reach`, `edit.py` calling it there: a sibling import from `commands/edit.py`
would bind two unrelated commands. Alternative: compute both **Hulls**, twice the reading for the same answer.

### Patterns are named, line-wise, case-insensitive where prose

Each pattern is `(name, category, regex)`, its name `<category>.<what>`, e.g. `run.pipe-to-shell`, `send.url`,
`privilege.sudo`, `permission.no-ask`. A line yields one **Flag** per matching pattern, so one line can carry several
categories (the pipe-to-shell scenario). Starting list, tuned in tests:

| Category       | Patterns                                                                                                                                                                                                                                                                                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `read`         | `outside-path`, `secret-store` (`.ssh`, `.aws`, `.gnupg`, `.env`, `.netrc`, `.npmrc`, `.pypirc`, `id_rsa`, `id_ed25519`, keychain, `credentials`)                                                                                                                                                                                                                                     |
| `write`        | `outside-path` on a line with `>`, `>>`, `tee`, `cp`, `mv`, `install`, `ln`, `mkdir`, `touch`, `sed -i`, or `write`, `save`, `append` (words)                                                                                                                                                                                                                                         |
| `send`         | `url` (a scheme and `://`), `network-tool` (`curl`, `wget`, `nc`, `ncat`, `scp`, `rsync` to a host, `ssh`, `Invoke-WebRequest`), `network-call` (`requests.`, `urllib`, `httpx`, `fetch(`, `socket`), `web-tool` (`WebFetch`, `WebSearch`), `push` (`git push`, `gh pr create`, `gh gist`), `mail`                                                                                    |
| `run`          | `shell-block` (a fence opening `sh`, `bash`, `zsh`, `shell`, `console`, `powershell`), `pipe-to-shell`, `eval` (`eval`, `exec(`, `os.system`, `subprocess`, `sh -c`, `bash -c`), `destructive` (`rm -rf`, `dd if=`, `mkfs`, `shred`, a fork bomb), `executable` (the bit, line 0), `shebang` (line 1)                                                                                 |
| `privilege`    | `sudo`, `su`, `doas`, `pkexec`, `runas`, `world-writable` (`chmod 777`, `o+w`, `a+w`), `setuid` (`u+s`, `g+s`, a 4- or 2-prefixed mode), `chown-root`                                                                                                                                                                                                                                 |
| `persistence`  | `agent-config` (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/`, `.cursor/`, `.codex/`, `settings.json`, `.mcp.json`), `hooks` (a `hooks:` front matter key, `.git/hooks`, `hooks` in agent settings), `shell-rc` (`.bashrc`, `.zshrc`, `.profile`, `.bash_profile`, `config.fish`), `scheduler` (`crontab`, `cron.d`, `systemctl enable`, `launchctl`, `LaunchAgents`, `schtasks`) |
| `permission`   | `tool-grant` (an `allowed-tools:` front matter key in `SKILL.md`), `skip-prompts` (`--dangerously-skip-permissions`, `bypassPermissions`, `--permission-mode`, `--yolo`), `no-ask` ("without asking", "do not ask", "don't tell the user", "silently", "quietly", "do not mention")                                                                                                   |
| `unreviewable` | `binary`, `encoding` (decodes, but not as strict UTF-8; line 0), `long-line` (over 1000 characters), `encoded-blob` (200 or more base64 or hexadecimal characters in a row)                                                                                                                                                                                                           |

Front matter is the block between a first line `---` and the next, in `SKILL.md` only. Commands match on word boundaries
so `subprocess` does not flag `su`. Every pattern has a test that it flags its line and one that it leaves a near miss
alone.

### Paths outside the project

One regex finds path-like tokens; a token is outside when it starts with `/`, `~`, `$HOME` or `${HOME}`, or when its
`..` parts outnumber the parts before them (`posixpath.normpath` starting with `..`). A URL's path is no path: tokens
inside a `scheme://` are skipped. Write vs read is decided per line by the write markers above.

### Files

Each file of the view is decoded by `hidden.decode_as(data, markdown, "replace")`: `None` is `unreviewable.binary` at
line 0, an encoding other than strict UTF-8 is `unreviewable.encoding` at line 0 and its text is still scanned. Lines
split on `\n`, numbered from 1, as `hidden.py` numbers them. The executable bit comes from the view.

### Output

Lines are `" ".join([skill, f"{name}:{line}", category, ",".join(ids), pattern])`, where `name` maps each character
outside `!`..`~` to `?`: stricter than `text.show`, as the line is split on spaces by the `graft-vet` filter. The
**Skill ID** needs no mapping, its parts matching `[A-Za-z0-9._-]`. Sorted by **Hull** order, then the file's path bytes
(the view's order), line, pattern; duplicates dropped. The closing notice goes through `errors.notice`, so it precedes
the warnings.

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

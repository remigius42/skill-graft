# Proposal

## Why

The user can see why a **Skill** is in the **Hull** only by running `resolve` and reading the tree from the top, and can
change **Entries** and **Renames** only by editing `skill-graft.toml` by hand. A **Skill** reached through many paths,
or a **Hull** to show in documentation, needs a direct view. Accepting a prose suggestion, or undoing one, should be one
command that checks the result before it writes anything. The commands also lack help text.

## What Changes

- **`why <skill>`**: an inverted tree, like `cargo tree -i`. The root is the **Skill**; each child is a **Skill** whose
  slash or Skill tool **Reference** reaches it, joined by `├─←`/`└─←`, up to the **Entries**, marked `(entry)`.
  `<skill>` is a **Skill ID** (holds `/`) or a **Deployed name**. A bare upstream name of a renamed **Skill**, or a
  **Skill** outside the **Hull**, is an error with a hint.
- **`tree [--format text|mermaid] [--link]`**: `resolve`'s tree without the suggestions, or a Mermaid `flowchart TD`.
  `--link` prints a `https://mermaid.live/edit#pako:…` URL that holds the diagram in its fragment: nothing is uploaded,
  and no network call is made.
- `why` and `tree` resolve in memory, as `resolve` does, and write nothing. They never read the lock, which stays output
  only.
- **`add <skill-id>…`**, **`remove <skill-id>…`**, **`rename <skill-id> <name>`**: they edit `entries` or `[rename]` in
  place (comments and formatting survive, a symlink stays a symlink), resolve the edited config before writing, then
  write the TOML and the lock and print what `resolve` prints. A failure writes nothing. Renaming a **Skill** to its
  upstream name removes its key; that is how a **Rename** is undone.
- **Help**: `-h`/`--help` on every command, with descriptions in the glossary's terms. `skill-graft help [command]`
  prints the same text. No command, or an unknown one, prints the error and the command list and exits 2.
- `resolve`'s suggestion header names `skill-graft add` instead of editing `entries`.

Out of scope: commands that edit **Binds**, **Patches**, **Sources** or `reserved`; links from the Mermaid diagram to
the **Sources**; opening a browser.

## Capabilities

### New Capabilities

- `explain`: `why` and `tree`: reading the **Hull** without writing anything; text, Mermaid and the mermaid.live link.
- `edit`: `add`, `remove`, `rename`: editing `skill-graft.toml` in place, resolve before writing, notices.
- `cli`: help on every command, the `help` command, usage errors.

### Modified Capabilities

- `resolve`: prose suggestions say to accept them with `skill-graft add`.

## Impact

- New: `src/skill_graft/explain.py` (reverse tree, Mermaid, link) and `src/skill_graft/edit.py` (TOML edits), with
  tests.
- Changed: `cli.py` (new subcommands, help, `help` command, exit 2 on usage errors); `lock.py` (the suggestion header;
  the tree function shared with `tree`); `update.py` (its in-place TOML write is shared with `edit.py`).
- `docs/design.md` (already settled), `README.md`: the new commands.
- No new runtime dependency: the link uses `zlib`, `base64` and `json`.

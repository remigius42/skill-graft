# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and **Sources**.

## 1. bind

- [x] 1.1 `edit.bind` sets a new or existing `[bind]` key to a **Skill ID** or `false`, appending the table when
  absent and keeping a replaced value's comment; verify tests for the edit spec's "New bind", "Bind to nothing"
  and "Replaced" scenarios pass
- [x] 1.2 `bind` with the current value, `false` included, is a notice that leaves the file's bytes, after the
  target is checked; verify tests for "Already bound so", "Already bound to nothing" and "Already bound to a
  skill gone upstream" pass
- [x] 1.3 `bind` refuses an unknown or malformed target and a malformed or undeclared key, and writes an unused
  **Bind** with its warning; verify tests for the "Bind checks its key and target" scenarios pass
- [ ] 1.4 Wire `bind` into the CLI (parser with help text, `WRITERS`) and list it in `README.md` and
  `docs/design.md`; verify the CLI tests for top-level help, `bind --help`, a missing argument (exit 2) and the
  `package:` line pass

## 2. unbind

- [ ] 2.1 `edit.unbind` parses its key as `bind` does, deletes it from `[bind]`, leaving the table, and errors on
  a key that is not there; verify tests for the "Unbind a name" scenarios pass, including the one where
  resolution fails and the undeclared alias
- [ ] 2.2 Wire `unbind` into the CLI and list it in `README.md` and `docs/design.md`, adding `unbind` to `words`
  in `.cspell.yaml`; verify the CLI tests for top-level help, `unbind --help`, a missing argument (exit 2) and
  the `package:` line pass and `pre-commit run --all-files` is green

## 3. Messages

- [ ] 3.1 The unmatched-**Reference** warning and the ambiguity error suggest `skill-graft bind`; verify tests for
  the hull spec's "No such skill" and "Several other sources" scenarios pass
- [ ] 3.2 `hull.walk` checks the target of every **Bind**, used or not; verify tests for "Unused bind to a missing
  skill" and "Typo in a bind" pass, with existing fixtures given the targets their binds name
- [ ] 3.3 `resolve.known` fetches only the **Source** of the **Skill ID** it checks; verify a test where another
  git **Source**'s remote is unreachable and `rename` and `bind` still succeed past the check

## 4. Wrap-up

- [ ] 4.1 Mention `bind` and `unbind` in the `edit` spec's Purpose and the `edit.py` docstring, and update
  `docs/design.md` where it says no command edits binds, lists the no-op edits, quotes the unmatched-**Reference**
  warning and describes when a **Bind**'s target is checked; verify `openspec validate bind-command --strict`
  passes

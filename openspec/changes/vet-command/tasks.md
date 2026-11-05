# Tasks

Test-first: each task's test fails before its code, then passes. One commit per task.

## 1. Shared reach

- [x] 1.1 Move `_reach` from `commands/edit.py` to `pipeline/hull.py` as `reach`, `edit.py` calling it there, with a
  test in `tests/pipeline/test_hull.py` for a two-level reach; verify `uv run pytest` and `lint-imports` pass

## 2. The scan (`pipeline/vet.py`, `tests/pipeline/test_vet.py`)

- [x] 2.1 `Flag`, the eight categories and the OWASP table; `scan` over a `deployed.View` yielding nothing yet; verify a
  test pins the table as the spec lists it (vet, "Categories and their OWASP IDs")
- [x] 2.2 File decoding: `unreviewable.binary` and `unreviewable.encoding` at line 0, a UTF-16 file still scanned; line
  numbers as `hidden.py`'s; verify the "Binary file" scenario and a UTF-16 case pass
- [x] 2.3 Paths outside the project and secret stores: `read.outside-path`, `write.outside-path`, `read.secret-store`,
  URL paths skipped; verify the "Outside the project by form" scenarios pass
- [x] 2.4 `send` and `run` patterns, the executable bit and the shebang; verify "Pipe to a shell", "A send Flag" and a
  hit and a near miss per pattern pass
- [x] 2.5 `privilege` and `persistence` patterns, word boundaries (`subprocess` is no `su`); verify "A secret store",
  "Agent config" and a hit and a near miss per pattern pass
- [x] 2.6 `permission` patterns and `SKILL.md` front matter (`allowed-tools`, `hooks`); verify "Tool grant", "Not
  asking", and that `allowed-tools` outside front matter or in another file is no `permission.tool-grant`
- [x] 2.7 `unreviewable.long-line` and `unreviewable.encoded-blob`; verify "Encoded blob" and a 199-character run left
  alone

## 3. The command (`commands/vet.py`, `cli.py`)

- [x] 3.1 `skill-graft vet` without arguments: compute the **Hull** as `tree` does, scan each **Skill** as deployed
  (rewrites applied), print the **Flag** lines sorted and de-duplicated, the closing notice; verify in
  `tests/commands/test_vet.py` "No lock", "A Patch removes a line", "A Patch adds a line", "A script", "Matched text is
  never printed", "A file name with a space", "Flags found", "Nothing flagged", and that the lock, config and
  `.apm/skills/` bytes are unchanged
- [x] 3.2 With **Skill IDs**: those in the **Hull** alone, one outside it with what its `add` brings in, unknown and
  repeated IDs; verify "A Hull Skill", "A Skill not yet added", "Unknown Skill", and `skill-graft.toml` unchanged
- [x] 3.3 Errors as `resolve`'s: a **Hidden character**, a failing **Patch**, a `[vet]` table; verify "Hidden character"
  and "An unknown key" exit 1 with no **Flag** on standard output
- [x] 3.4 Help: `vet` in the top-level list and `skill-graft vet --help` in the glossary's terms; verify in
  `tests/cli/test_cli.py`

## 4. Docs

- [ ] 4.1 `README.md` Commands: `vet`, what a **Flag** line holds, that it never judges; verify the hooks and
  `check-pins` pass
- [ ] 4.2 `docs/security.md`: the Future work item becomes a section on the **Vet**; Residual risks and the OWASP rows
  (LLM01, LLM03, ASI05) say what it narrows and what it does not; `docs/architecture.md` lists `pipeline/vet.py` and
  `commands/vet.py` if it lists modules; new words in `.cspell.yaml`; verify every relative link resolves and the hooks
  pass

## 5. Check

- [ ] 5.1 Run `uv run pytest`, `uv run mypy .` and `openspec validate vet-command --strict`; verify all pass

# Tasks

Test-first: each task's test fails before its code, then passes. One commit per task.

## 1. `vet --into`

- [x] 1.1 Move `deploy`'s `_check_into` and `_check_into_sources` to `commands/transaction.py` as `check_into` and
  `check_into_sources`, `deploy.py` calling them there; verify `uv run pytest tests/commands/test_deploy.py` and
  `lint-imports` pass
- [x] 1.2 `vet --into <dir>`: checked as `deploy --into`'s folder, each vetted **Skill** written to
  `<dir>/<alias>/<name>/` after every scan, `<dir>` emptied on a failed write; verify in `tests/commands/test_vet.py` "A
  Skill not yet added", "Patched and renamed", "A Skill with no Flag", "Folder not empty", "Hidden character", and the
  lock, config and `.apm/skills/` bytes unchanged
- [x] 1.3 `--into` in `cli.py` and `vet --help`; verify "Empty value" and the help in `tests/cli/test_cli.py`
- [x] 1.4 `vet` names the **Package** on its first standard error line, `skill-graft: package: <package>`, as the
  writing commands do, before loading the config (added: the design took it as given, but `vet` did not print it, and
  the skill reads it); verify in `tests/commands/test_vet.py`, its own stderr and a failure's

## 2. The skill's files (`skills/graft-vet/`, `tests/cli/test_graft_vet.py`)

- [x] 2.1 `run-claude.sh`, a copy of graft-check's; verify a test that the two are byte for byte equal ("Runner drift")
- [x] 2.2 `reader.json`: `Read`, `Grep`, `Glob`, the eight categories by intent, the reply shape, `none`, `probe` mode,
  the untrusted-text paragraph, no pattern name of `pipeline/vet.py`; verify a test of its tools and prompt
- [x] 2.3 `report-filter.sh`, keeping and dropping: sanitizing, blank and fence lines skipped, `<dir>/<skill id>/` and
  `./` stripped, the line shape, only names of `<dir>/<skill id>/` as `vet` maps them and lines within them (awk's
  `NR`), at most 1000, every other line dropped and counted, no reply refused; verify "Well-formed reply", "A fenced
  reply", "An absolute path", "Free text", "Words as a file name", "Lines that are no place", "Last line with no line
  break", a name with a newline matching nothing, and line 1001 dropped
- [ ] 2.4 `report-filter.sh`, merging into the report file, and the summary on standard output: the line shape,
  `seen-by`, a scan **Flag**'s OWASP IDs copied from its `vet` line and a reader-only one's from its table, order,
  duplicates dropped, the status lines first; verify "Both", "Reader only", "A file name with a space", "Scan IDs as
  printed", "Words as file names", "A summary line", "The reader cannot choose seen-by or OWASP IDs", and a test that
  its table equals `pipeline/vet.py`'s
- [ ] 2.5 `report-filter.sh`, the steering count, once per file, line and category; verify "A steered reader", "Another
  line, same category", "Two patterns, one line", "Line 0 on neither side", "Only dropped lines", a `no-reply` count,
  "Two files, one mapped name", and a `both` **Flag** counting nothing

## 3. `SKILL.md`

- [ ] 3.1 Front matter and no other **Skill** named; verify "Front matter" and "Alone in its hull"
- [ ] 3.2 Steps: the probe as graft-check's, then the scan (`vet --into` hardened, plain `vet` not, its standard error
  unopened but for its first line naming the **Package**, a failure showing its exit code only), a fresh working folder
  per reader, unhardened going to the scan alone with no yes, readers per folder with `[check]`'s caps and batches, a
  failed reader's exit code and first error line, never its output, the filter, the quarantine; verify tests on its key
  sentences for "The scan is the CLI's", "A Package in user scope", "A warning names a Reference", "An error names a
  link target", "Hardened by the probe", "One reader per Skill", "Error output empty" and "The main agent never reads
  Skill text"
- [ ] 3.3 The report: the filter's summary, the report file's path for the user, `vet`'s output and the report file
  never opened, `skill-graft remove <id>` for a flagged **Entry** only, no verdict, the fixed caveats with every report;
  verify tests for "Reports only", "Caveats always", each caveat present, and "The main agent never reads Skill text"

## 4. Eval (`evals/graft-vet/`)

- [ ] 4.1 `run.sh` and `README.md`, the `injected` scenario as the design describes; verify `bash -n` and `shellcheck`
  pass and `run.sh` without a token stops before building anything. Do not run the scenario

## 5. Docs

- [ ] 5.1 `docs/security.md`: graft-vet's readers and filter in The Vet section, beside the **Check**'s, its Residual
  risks (a steered reader, **Skill IDs** reaching the main agent, category-level steering count, prompt-level
  quarantine, file names reaching the user only through the report file), the OWASP rows for its readers (LLM01, LLM02,
  LLM05, ASI05, ASI07, ASI08: one **Skill** per reader); verify every relative link resolves and the hooks pass
- [ ] 5.2 `README.md` Security and Commands (`vet --into`, graft-vet); new words in `.cspell.yaml`; verify the hooks and
  `check-pins` pass

## 6. Check

- [ ] 6.1 Run `uv run pytest`, `uv run mypy .`, `openspec validate graft-vet --strict`; verify all pass

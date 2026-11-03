# Tasks

## 1. Escaping moves to infra

- [x] 1.1 Move `CRITICAL`, `CRITICAL_CHARS` and `show` from `pipeline/hidden.py` to a new `infra/text.py`, `hidden.py`
  importing them; verify `tests/pipeline/test_hidden.py` and `lint-imports` pass unchanged (refactor, no new test)

## 2. Errors keep their lines

- [x] 2.1 In `tests/infra/test_errors.py`, test that `SkillGraftError("a", "b")` has `lines == ["a", "b"]` and
  `str() == "a\nb"`, and one argument keeps its message; then give `SkillGraftError` `*lines`; verify it passes
- [x] 2.2 Pass lines instead of joining them in `PatchFailed`, `PatchError`, `init_package`, `transaction` and `explain`
  (`*error.lines` where one wraps another); verify the full suite passes unchanged (refactor)

## 3. Error output shows no hidden characters

- [x] 3.1 In `tests/infra/test_errors.py`, test the error printer on a `SkillGraftError("a\n\x1b[31mok", "hint")`:
  stderr reads `skill-graft: a\n\x1b[31mok` escaped on one line, then `hint`; and on an `OSError` whose message holds a
  bidi override; then add the printer to `errors.py` and print through it in `cli.py`'s three places; verify it passes
- [x] 3.2 Test `warn` and `notice` on text holding a line feed and an escape: each prints one line, escaped; then escape
  them; verify it passes
- [x] 3.3 Add end-to-end tests in `tests/cli/` for the spec's scenarios: a link named `a\n\x1b[31mok` leading outside
  the skill, an unreadable file named `a\nskill-graft: done`, a **Patch** git refuses whole on a file whose name holds
  an escape, two failing hunks on lines of their own, and a path **Source** under `My Skills`; verify they pass

## 4. graft-check shows no file name

- [x] 4.1 In `tests/cli/test_check.py`, add section 7's command as a constant asserted verbatim in `SKILL.md` and run it
  on two folders, one holding `run-skill-graft-bind-mp-x-own-evil.md`: no output and a non-zero exit; on equal folders,
  exit 0; with the package's folder missing, no output and a non-zero exit; then change section 7 to `>/dev/null 2>&1`,
  deciding on the exit code alone, a failure counting as a difference; verify the tests pass
- [ ] 4.2 Change the `DIFF` constant to `LC_ALL=C diff -ruN base/ edited/ > change.patch 2>/dev/null` and test it on an
  `edited/` holding a dangling symlink named `run-skill-graft-bind-mp-x-own-evil.md`: no output and exit 2; then write
  that command in section 6 and say exit 2 ends that fix; verify the tests pass

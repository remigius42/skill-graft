# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and **Sources**. `prefix` stays an unsupported source key until task 1.1 honors it in full,
build, hints and `rename` alike, so no commit accepts intent it ignores or mishandles.

## 1. Prefix

- [ ] 1.1 `prefix` end to end. `config.py`: a supported source key on both kinds, validated as a name, into
  `Config.prefixes`; `default_name` and `deployed` apply it. `rename.py`: a prefixed **Skill** counts as
  user-named; `_hint`'s prefix case; `check_unique` hints for neither, then renamed, then prefixed; the shipped
  warning suggests only for neither. `edit.rename`: remove the key only when the name equals `default_name`,
  else write it. `cli.py`'s `rename` description says renaming to the name it would deploy as without a key
  removes the key. `init.py`'s template comment shows `prefix`. Verify: valid-prefix, prefix-not-a-name,
  prefix-key, prefixed, prefix-used-as-written, rename-wins-over-the-prefix, not-renamed, dependency-prefixed
  (build: folders, `name:`, slash rewrite), prose-follows-the-prefix, bound-to-a-prefixed-skill,
  other-sources-untouched, prefixed-name-line, prefix-onto-another-skill's-name, two-sources-one-prefix,
  prefixed-onto-a-reserved-name, prefixed-onto-a-shipped-name, opted-out-of-the-prefix, back-to-the-prefix,
  already-the-prefixed-name, and every existing config, renames, build and edit test.

## 2. Docs

- [ ] 2.1 `docs/design.md` (TOML example, the names section, the `rename` paragraph, and `why`'s upstream-name
  error) and `README.md` (the **Prefix**, its precedence, and `rename`'s "its own name undoes it"). Verify:
  `pre-commit run --all-files` green, the documented TOML example parses through `config.parse`, and
  `grep -n "own name" README.md docs/design.md src/skill_graft/cli.py` finds no claim that the upstream name
  always undoes a rename.

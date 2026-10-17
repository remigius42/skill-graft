# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and **Sources**. `prefix` stays an unsupported source key until task 1.1 honors it end to
end, so no commit accepts intent it ignores.

## 1. Prefix

- [ ] 1.1 `config.py`: `prefix` a supported source key on both kinds, validated as a name, into
  `Config.prefixes`; `default_name` and `deployed` apply it; `init.py`'s template comment shows `prefix`.
  Verify: valid-prefix, prefix-not-a-name, prefix-key, prefixed, prefix-used-as-written,
  rename-wins-over-the-prefix, not-renamed, dependency-prefixed (build: folders, `name:`, slash rewrite),
  prose-follows-the-prefix, bound-to-a-prefixed-skill, other-sources-untouched, prefixed-name-line,
  two-sources-one-prefix (exits non-zero naming both), and every existing config, renames and build test.
- [ ] 1.2 `rename.py` hints: a prefixed **Skill** counts as user-named; `_hint`'s prefix case; `check_unique`
  hints for neither, then renamed, then prefixed; the shipped warning suggests only for neither. Verify:
  prefix-onto-another-skill's-name, two-sources-one-prefix (its hint), prefixed-onto-a-reserved-name,
  prefixed-onto-a-shipped-name, and every existing hint scenario (clash-across-sources,
  rename-onto-another-skill's-name, clash-of-two-renames, reserved-by-the-user, shipped-clash).
- [ ] 1.3 `docs/design.md` (TOML example, names section) and `README.md`: **Prefix** and its precedence. Verify:
  `pre-commit run --all-files` green, and the documented TOML example parses through `config.parse`.

## 2. Rename command

- [ ] 2.1 `edit.rename`: remove the key only when the name equals `default_name`, else write it; `docs/design.md`'s
  `rename` paragraph says so. Verify: opted-out-of-the-prefix, back-to-the-prefix, already-the-prefixed-name,
  undone, already-that-name, and every existing edit test.

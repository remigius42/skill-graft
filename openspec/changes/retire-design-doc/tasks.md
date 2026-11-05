# Tasks

## 1. Docs

1.1 to 1.3 were committed before this proposal, which the branch rebases under them; 1.4 after it.

- [x] 1.1 Move the README's task guides into `docs/howto.md`, keeping Cache, which an error message names, in the
  README; verify every relative link and anchor resolves and `check-pins` passes
- [x] 1.2 Replace `docs/design.md` with `docs/architecture.md` and `docs/apm-behavior.md`, saying there why lone
  surrogates are in no class, and point `AGENTS.md` at the specs and `docs/architecture.md`; verify
  `grep -rn 'docs/design.md'` outside archived changes finds nothing
- [x] 1.3 Add `docs/README.md` and link CONTEXT.md, CONTRIBUTING.md, `docs/security.md` and the ADRs to it and each
  other; verify every relative link resolves
- [x] 1.4 Add the logo: `docs/assets/skill-graft.svg` and `docs/assets/skill-graft-small.svg`, the full mark in the
  README as `<img alt="" width="128" align="right">` from its `raw.githubusercontent.com` URL on `main`, `img` allowed
  in `.markdownlint.yaml`, and `docs/assets/` in `docs/README.md` with its size rule; verify the hooks pass,
  `twine check` passes, and `readme_renderer` keeps the `<img>` with its `width` and `align`

## 2. Pin the behaviors no test pins yet

Each should pass at once: the code already behaves so. One that fails is a bug, reported before any fix.

- [x] 2.1 `tests/commands/test_deploy.py`: after `resolve`, a comment line added to `skill-graft.lock` and CRLF line
  endings, and `deploy` exits 0 (deploy, "Lock reformatted by an editor"); verify it passes
- [x] 2.2 `tests/cli/test_hidden_characters.py`: a U+202E in a `skill-graft.toml` comment, and `resolve` exits 0
  (hidden-characters, "In the config"); verify it passes
- [x] 2.3 `tests/commands/test_review.py`: after a killed run leaves `.apm/skills.old/` holding the lock's copies,
  `resolve --dry-run` compares against those, through the command (edit, "After a killed run"); verify it passes
- [x] 2.4 `tests/pipeline/test_hull.py`: an entry holding a tag character calls `/notes`, which two other sources have,
  so the walk stops, and `hidden characters:` comes before that error (hidden-characters, "One run reports every hidden
  character"); verify it passes

The other scenarios are pinned already: the notice text by `tests/commands/test_deploy.py`, the link's `mermaid` field
and unpadded fragment by `test_mermaid_link_decodes_to_the_diagram` in `tests/commands/test_explain.py`, the headers'
order by `tests/pipeline/test_hull.py`.

## 3. Release-named links on PyPI

- [x] 3.1 `pyproject.toml`: build with hatchling and hatch-fancy-pypi-readme, `readme` dynamic, substitutions turning
  each relative Markdown link and `src` into `blob/v$HFPR_VERSION/` and `raw.githubusercontent.com/…/v$HFPR_VERSION/`;
  verify `uv build` holds the same wheel and sdist files as `uv_build` did, but for the sdist's `.gitignore`, which
  hatchling always adds, and `pyproject.toml.orig`, which only `uv_build` wrote, `twine check` passes, and
  `uv tool install` from the worktree runs `skill-graft --version`
- [ ] 3.2 Point the README's links to `docs/` and CONTEXT.md, and the logo's `src`, at relative paths, leaving
  `SECURITY.md`, CONTRIBUTING.md, LICENSE and the badges on `main`; verify every relative link resolves in the working
  tree, and the built README's links all name `blob/v0.4.0/` or `raw.githubusercontent.com/…/v0.4.0/`, with no relative
  one left
- [ ] 3.3 `tests/cli/test_pypi_readme.py`: build the wheel and read its `METADATA` description; fail on a relative link
  or `src` left, or a `blob/v` link naming another version than `pyproject.toml`'s or a file missing from the working
  tree; verify it fails against a README with a link the substitutions miss, then passes

## 4. Check

- [ ] 4.1 Run `uv run pytest` and `openspec validate retire-design-doc --strict`; verify both pass

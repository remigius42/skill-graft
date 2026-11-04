# Tasks

## 1. Docs

All three were committed before this proposal, which the branch rebases under them.

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
- [ ] 2.2 `tests/cli/test_hidden_characters.py`: a U+202E in a `skill-graft.toml` comment, and `resolve` exits 0
  (hidden-characters, "In the config"); verify it passes

The other scenarios are pinned already: the notice text by `tests/commands/test_deploy.py`, the link's `mermaid` field
and unpadded fragment by `test_mermaid_link_decodes_to_the_diagram` in `tests/commands/test_explain.py`, the headers'
order by `tests/pipeline/test_hull.py`, `.apm/skills.old/` by `test_killed_run_reads_skills_old` in
`tests/commands/test_review.py`.

## 3. Versioned docs links

- [ ] 3.1 `scripts/check_pins.py`: a pair `skill-graft blob/v`, each README link's `blob/v<version>/` against
  `pyproject.toml`'s version, with cases in `tests/test_check_pins.py` for a match, a mismatch and none found; verify
  the new tests fail first, then pass
- [ ] 3.2 Point the README's links to `docs/` and CONTEXT.md at `blob/v0.4.0/`, leaving `SECURITY.md`, CONTRIBUTING.md,
  LICENSE and the badges on `main`; verify `check-pins` passes and every such link names a path that exists in the
  working tree; links to files the tag lacks 404 until the release commit raises them, as design.md accepts
- [ ] 3.3 CONTRIBUTING.md's release steps: raise each `blob/v<previous version>` with the other pins; verify the
  pre-commit hooks pass

## 4. Check

- [ ] 4.1 Run `uv run pytest` and `openspec validate retire-design-doc --strict`; verify both pass

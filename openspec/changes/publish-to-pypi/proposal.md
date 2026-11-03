# Proposal

## Why

The package is named `skill-graft`, and as of 2026-11-03 nobody owns that name on PyPI. A user who types
`pip install skill-graft` or `uvx skill-graft`, as one does for a Python tool, gets whatever someone else uploads under
it, and that code runs on install with the user's rights. The README's "It is not on PyPI" helps only the people who
read it. PyPI cannot reserve a name, and an empty placeholder can be taken back under PEP 541, so the name is claimed by
publishing the real releases.

## What Changes

- Each release goes to PyPI as `skill-graft`: a GitHub Actions workflow builds the sdist and wheel from the signed
  release tag and uploads them by trusted publishing (OIDC, no stored token), with the attestations PyPI shows for them.
  The workflow refuses a tag whose signature does not check against the README's key, or whose version is not
  `pyproject.toml`'s.
- The workflow runs when a `v*` tag is pushed, and can be started by hand for an existing tag: that is how 0.4.0 goes up
  once this change is on main. Either way, the upload waits for the maintainer to approve it on GitHub, so a pushed tag
  alone publishes nothing.
- The README's Installation leads with PyPI (`uv tool install skill-graft==<version>`, pipx, pip, pipenv). Installing
  from the repository at a signed tag stays, as the way to check what you install against the tag's signature, and to
  install the unreleased `main`. Its links to other files become absolute, as the README is also the PyPI project page.
- `check-pins` pairs the README's `skill-graft==<version>` with `pyproject.toml`'s version, as it does the `@v<version>`
  URLs, so a release that bumps one fails until the other follows.
- `CONTRIBUTING.md`'s Releasing: replace `==<previous version>` too, wait for the publish run after pushing the tag, and
  approve its upload, and the one-time PyPI setup (pending publisher, the `pypi` environment). A version once uploaded
  cannot be uploaded again: a wrong release is yanked on PyPI and fixed by a patch release.

Not in scope: publishing to TestPyPI, and any change to `skill-graft --version`, which already prints the version alone
for a package-index install.

## Capabilities

### New Capabilities

- `distribution`: where a release of skill-graft can be installed from, and what ties each published copy to its signed
  release tag.

### Modified Capabilities

## Impact

- `.github/workflows/publish.yml` (new): build, verify the tag, upload; actions pinned by SHA like `ci.yml`, kept up by
  the existing Dependabot `github-actions` entry.
- `scripts/check_pins.py`, `tests/test_check_pins.py`: the `skill-graft==<version>` side of the README/version pair.
- `README.md` (Installation), `CONTRIBUTING.md` (Releasing, Tooling); `CHANGELOG.md` at archive.
- Outside the repository, by hand: a pending publisher for `skill-graft` on pypi.org, and a `pypi` environment in the
  GitHub repository settings, with the maintainer as its required reviewer.

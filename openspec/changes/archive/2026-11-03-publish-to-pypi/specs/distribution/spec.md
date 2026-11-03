# Spec Delta

## Purpose

Where a release of skill-graft can be installed from, and what ties each copy published on PyPI to the signed release
tag it was built from.

## ADDED Requirements

### Requirement: Releases on PyPI

Each release from 0.4.0 on SHALL be published on PyPI as `skill-graft`, at the version its tag `v<version>` names, as an
sdist and a wheel. Installing `skill-graft==<version>` from PyPI SHALL install the same files as installing from the
repository at `v<version>`.

#### Scenario: Install a release from PyPI

- **WHEN** release 0.5.0 is tagged `v0.5.0` and the user runs `uv tool install skill-graft==0.5.0`
- **THEN** it installs, and `skill-graft --version` prints `skill-graft 0.5.0`

#### Scenario: Release older than the change

- **WHEN** this change is on main and the maintainer starts the publish workflow for the existing tag `v0.4.0`
- **THEN** PyPI holds `skill-graft` 0.4.0, built from that tag

### Requirement: Built only from a signed tag

The upload SHALL be built from a tag `v<version>` whose signature checks against the key the README names, and whose
`<version>` is `pyproject.toml`'s version at that tag, and from that tag's commit only. Otherwise nothing SHALL be
uploaded, and the run SHALL fail naming what did not match.

#### Scenario: Unsigned tag

- **WHEN** a tag `v0.5.0` is pushed without a signature, or signed with another key
- **THEN** the publish run fails before uploading, naming the tag's signature

#### Scenario: Tag and version disagree

- **WHEN** the tag `v0.5.0` points at a commit whose `pyproject.toml` names version `0.4.0`
- **THEN** the publish run fails before uploading, naming both versions

### Requirement: Upload waits for approval

No upload SHALL start before the maintainer has approved that run on GitHub. A run nobody approves SHALL upload nothing.

#### Scenario: Tag pushed, not approved

- **WHEN** the signed tag `v0.5.0` is pushed and its build passes
- **THEN** the run waits for approval, and PyPI does not hold 0.5.0 until the maintainer approves

#### Scenario: Approved

- **WHEN** the maintainer approves that run
- **THEN** it uploads 0.5.0

### Requirement: Uploads are attested

Each uploaded file SHALL carry an attestation, shown on PyPI, that names this repository and the publish workflow as its
origin, and the upload SHALL authenticate by trusted publishing, with no long-lived PyPI token stored anywhere.

#### Scenario: Provenance on PyPI

- **WHEN** a release has been published
- **THEN** PyPI shows each of its files as published from `remigius42/skill-graft` by the publish workflow

### Requirement: README installs and version agree

The README SHALL name the release both as `skill-graft==<version>` and as `skill-graft@v<version>`, and every version it
names in either form SHALL be `pyproject.toml`'s. The hooks SHALL refuse a commit in which either form is missing or
names another version, naming the form.

#### Scenario: Release bumps only the URLs

- **WHEN** a commit sets `pyproject.toml`'s version to 0.5.0 and the README's URLs to `@v0.5.0`, but leaves
  `skill-graft==0.4.0`
- **THEN** `check-pins` fails naming `skill-graft==`, `0.4.0` in `README.md` and `0.5.0` as `pyproject.toml`'s version

#### Scenario: PyPI install lines removed

- **WHEN** a commit rewrites every `skill-graft==<version>` in the README to an unpinned `uv tool install skill-graft`
- **THEN** `check-pins` fails naming `skill-graft==` as not found in `README.md`

### Requirement: Manual start takes only a release tag

A manual start SHALL build only the tag `v<digits>.<digits>.<digits>` its input names, never a branch of that name, and
SHALL refuse any other input before checking anything out.

#### Scenario: Input not a release tag

- **WHEN** the maintainer starts the publish workflow with the input `v0.4.0; true`
- **THEN** the run fails before checkout, naming the input, and runs no part of it as a command

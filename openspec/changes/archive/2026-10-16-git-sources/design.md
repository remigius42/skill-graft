# Design

## Context

From vendor-entries: `config.load()` returns `Config(sources: dict[str, Path], entries, warnings)`, path sources
only, and rejects `git`. `vendor.vendor()` resolves every **Entry** (`discovery.index`/`find`), checks
deployed names and symlinks, then copies and swaps. `paths.py` derives everything from `Path.home()`. Tests set
`HOME` to `tmp_path/home`; `fake_apm` replaces `PATH` with its own folder only. Git 2.55 is installed locally.

Decided while grilling (see the specs): fetch a missing **Ref** but never move it; cache per URL; any git source
without `ref` fails `build`; `update` writes only after resolution succeeds; `--dry-run` leaves the cache alone;
naming a path source in `update` is an error; **Ref** joins `CONTEXT.md`. After review: `git` is an allowed URL
or an absolute path, never relative; the cache repository takes the remote's hash format; checkouts are exact
exports of the committed bytes; git and ssh prompt as they do in the user's shell.

## Goals / Non-Goals

**Goals:** reproducible builds from git; `update` as the only thing that moves a **Ref**; the user's TOML kept
byte for byte apart from the shas.

**Non-Goals:** cache pruning, shallow or partial clones, submodules, LFS, tags as refs, credentials handling
beyond what git does itself.

## Decisions

- **Config model**: `Config.sources: dict[str, Source]`, where `Source` is `PathSource(folder)` or
  `GitSource(url, branch, ref)`, `branch` and `ref` optional. `load()` validates the kind and types; it does not
  require `ref` (so `update` can load a source without one). Loading runs no git, so a `branch` is rejected there
  only when empty or starting with `refs/` or `-`; `update` checks it fully with
  `git check-ref-format refs/heads/<branch>` before contacting the remote, so revision syntax (`main~3`,
  `main@{1}`) never resolves to another commit. Not `--branch`, which expands `@{-1}` in whatever repository the
  user runs skill-graft from.

- **`git` value**: `https://`, `http://`, `ssh://`, `git://` or `file://`; the scp-like form
  (`[user@]host:path`, no `/` before the `:`); or an absolute local path. Anything else is an error: a relative
  path would resolve against whatever folder git runs in; a leading `-` would be read as an option; another
  scheme, or `<transport>::<address>`, makes git run a remote helper (`ext::` runs commands). Commands that take
  the URL on the command line put `--` before it.

- **Cache layout** (`paths.cache()`): `$XDG_CACHE_HOME/skill-graft` when that is an absolute path (XDG spec),
  else `~/.cache/skill-graft`. Repository `repos/<key>.git`, exports `trees/<key>/<sha>/`, with
  `key = <name>-<sha256(url)[:12]>`, where `<name>` is the last URL segment once trailing `/` and `.git` are
  stripped, characters outside `[A-Za-z0-9._-]` replaced by `_`, and `repo` if that leaves nothing: readable,
  and distinct per URL.

- **`git.py`**, one runner: `subprocess.run(["git", *args], capture_output=True)`, stdin inherited, with the
  variables that redirect git to another repository (`GIT_DIR`, `GIT_OBJECT_DIRECTORY`, …, as a git hook sets
  them) removed, since skill-graft always names its repository with `--git-dir`. No prompt
  overrides: git and ssh ask for credentials, passphrases and host keys on `/dev/tty`, as in the user's shell,
  and the user's git config (`core.sshCommand`, credential helpers, `insteadOf`) applies. Clones and fetches
  pass `-c transfer.fsckObjects=true`, so git rejects malformed trees (paths with `..` or `.git`) before they
  are exported. `FileNotFoundError` → "git is not installed"; non-zero exit → `SkillGraftError` with alias, URL
  and git's stderr.

- **Repository**: a bare clone (`clone --bare --no-tags -- <url> <tmp>`) into a folder unique to this run
  (`mkdtemp` beside the final name), then a rename into place; if another run got there first, ours is dropped.
  A killed clone leaves only garbage, never blocking the next run nor mistaken for a repository. Clone, unlike
  `init`, takes the remote's hash format (SHA-1 or SHA-256) from the protocol. Fetch:
  `git fetch --prune --no-tags origin +refs/heads/*:refs/heads/*`, all branches since the **Ref** may be on any.
  A `Cache` fetches each URL at most once per command, however many aliases name it. A clone or fetch holds
  `repos/<key>.git.lock` (`fcntl.flock`, POSIX like the rest), so a concurrent run waits rather than failing on
  git's ref locks; lock files stay, as `flock` needs. "Has commit" is
  `git cat-file -e <sha>^{commit}`.

- **Export at the ref**: `Cache.checkout(alias, url, ref) -> Path`. If `trees/<key>/<sha>/` exists, reuse it: it only
  ever appears complete. Otherwise ensure the commit (fetch only if missing; still missing → "ref not found"
  error), and write the tree into a folder unique to this run from `git ls-tree -r -z --full-tree <sha>`
  and one `git cat-file --batch` process: mode `100644` a file, `100755` a file with its exec bit, `120000` a
  symlink whose target is the blob, `160000` (submodule) skipped. A path with an empty, `.` or `..` part, or a
  `.git` part in any case, is refused, as a second guard behind fsck (clones use `--no-local`, so fsck checks
  local paths too). Symlinks are written last, and no
  file lands where a resolved parent leaves the folder or a path already exists. Then rename it to `<sha>/`, or
  drop it if another run got there first. These are the committed bytes exactly: no `.gitattributes`
  conversion, no filter drivers from the user's config, no `export-ignore` dropping (as `git archive` would),
  and no worktree or index state to go stale. A cached commit is used without asking the remote whether it
  still exists.

- **Resolution step shared by build and update**: split `vendor.vendor()` into
  `resolve(config, folders)`, returning each **Entry**'s folder (deployed names, `find`, symlink checks), and the
  copy-and-swap. `folders(config, cache, refs)` maps each alias to its folder: path as is, git via `checkout` at
  `refs[alias]`, which defaults to its `ref`. `build` first fails on any git source without `ref`.

- **`update`**: load → select aliases, check every unselected git source has a `ref`, and check each selected
  `branch` with `check-ref-format` (errors before any network) → per URL and branch, one `ls-remote`: without
  `branch`, `git ls-remote --symref -- <url> HEAD` gives `ref: refs/heads/<b>\tHEAD` and `<sha>\tHEAD`, and a
  missing sha line (no `HEAD`, or `HEAD` naming a branch that does not exist) is the "no default branch" error
  suggesting `branch = "…"`; with `branch`, `git ls-remote -- <url> refs/heads/<b>`, where no line is the
  "no branch" error → tip = that sha, fetched only when not in the cache → `folders` with the new tips →
  `resolve` → print lines → on success, not dry run, some change: write the TOML. On a resolution error the
  lines are printed first, then the error, exit 1.

- **Dry run**: the same code with a `Cache` rooted in a `tempfile.TemporaryDirectory`, holding the real cache
  as a read-only reference. For each commit it needs, in order: an export already in the real cache is used as
  is; a commit in the real repository is exported from it into the temporary folder (`ls-tree` and `cat-file`
  write nothing); otherwise the repository is cloned into the temporary folder with
  `--reference-if-able <real repository>` and fetched there. So a dry run contacts a remote exactly when a real
  `update` would, and never writes the real cache.

- **TOML edit** (`tomlkit`, new runtime dependency): parse the original text, set
  `doc["sources"][alias]["ref"]`, keeping the old item's trivia (trailing comment, indentation) when replacing.
  The target is `skill-graft.toml` resolved, so a symlinked file stays a symlink and its target changes: a
  temporary file in the target's folder, mode copied, then `os.replace` onto the target. Skipped when no sha
  changed. Inline tables (`mp = { git = "…" }`) work the same through tomlkit.

- **Tests**: `conftest` unsets `XDG_CACHE_HOME` and `XDG_CONFIG_HOME`, points `GIT_CONFIG_GLOBAL` at an empty
  file, and sets `GIT_CONFIG_NOSYSTEM=1` and `GIT_AUTHOR_*`/`GIT_COMMITTER_*`, so no developer git config
  (signing, `insteadOf`, default branch) reaches a test. A helper builds a synthetic upstream with
  `git init -b main` (optionally `--object-format=sha256`) and commits fixture skills, returning shas; its URL
  is its absolute path. `fake_apm` puts a symlink to the real `git` beside its fake `apm`, so build tests still
  find git while `apm` stays faked. Git-missing tests set `PATH` to an empty folder. Tests never use ssh, so no
  prompt can appear.

## Risks / Trade-offs

- [tomlkit loses a trailing comment on assignment] → a test with comments around and after `ref` fixes the
  behavior; copy the trivia if needed.
- [Full clones of large repositories are slow] → acceptable for skill repos; `--filter=blob:none` is a later
  option.
- \[The cache grows by one export per **Ref**\] → harmless and deletable; pruning is a later change.
- [A cached commit force-pushed away upstream still builds here but not on a fresh machine] → accepted: `build`
  never asks the remote about a commit it has; `update` moves the **Ref** to one that exists.
- [Hash-format detection depends on clone over the transport in use] → a remote git cannot detect fails the
  clone loudly, never silently with the wrong format; the SHA-256 test covers local clones.
- [Without prompt overrides, a non-interactive run (cron, CI) can wait on a prompt] → skill-graft is an
  interactive command; such users set `GIT_TERMINAL_PROMPT=0` or `BatchMode` themselves, which git honors.
- [The export reads every blob of the commit into memory at once, about twice the tree's size] → acceptable
  for skill repositories, which are small; streaming `cat-file --batch` through a pipe is the fix if one is not.
- [The export reimplements a small part of checkout] → modes are only four; a test covers each, plus CRLF
  attributes and a filter driver that must not apply.

## Migration Plan

None: existing path-only configs load unchanged. `docs/design.md`'s `update` bullet becomes "resolves, then
writes only on success".

## Open Questions

None.

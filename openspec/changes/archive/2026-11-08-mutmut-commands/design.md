# Design

## Context

`nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.commands.*"` on `afa64801` left 191 survivors of 2 339 mutants,
the count of the baseline's `commands` row. Each one's diff, read once (`mutmut show`), falls in one of seven kinds:

| Module         | Survivors | To kill | Bug | Dropped | Pragma | mypy refuses | Wording | Import |
| -------------- | --------: | ------: | --: | ------: | -----: | -----------: | ------: | -----: |
| `edit`         |        40 |      12 |   0 |       5 |      0 |           15 |       8 |      0 |
| `review`       |        38 |      21 |   0 |       2 |      2 |            6 |       3 |      4 |
| `explain`      |        27 |      15 |   0 |       5 |      0 |            3 |       4 |      0 |
| `update`       |        27 |       4 |   1 |      11 |      1 |            9 |       1 |      0 |
| `deploy`       |        20 |      13 |   0 |       3 |      0 |            4 |       0 |      0 |
| `vet`          |        17 |       9 |   0 |       0 |      0 |            6 |       2 |      0 |
| `transaction`  |        11 |       3 |   0 |       0 |      0 |            2 |       6 |      0 |
| `init_package` |         6 |       1 |   0 |       1 |      0 |            2 |       2 |      0 |
| `resolve`      |         3 |       1 |   0 |       1 |      0 |            1 |       0 |      0 |
| `scope`        |         2 |       1 |   0 |       0 |      0 |            0 |       1 |      0 |
| all            |       191 |      80 |   1 |      28 |      3 |           48 |      27 |      4 |

`housekeeping` has none. "Dropped" are equivalent mutants a removed redundancy or a restructure leaves without a
counterpart; "Pragma" the equivalent ones that stay, each marked. The mypy kind is mostly `cast(None, …)`, `None` for a
`str` context or `where`, and a flag assigned `None`. The wording kind includes the command name each edit passes to
`compute.known` and `config.parse_skill_id`, which only prefixes their errors. The import kind is `review.header`, which
runs only to build each command's module-level `HEADER`. One survivor is a bug (below). Mutant numbers are mutmut's at
`afa64801`; they shift with edits, so each task reruns its module first.

Applied, three survivors were classed otherwise: `fetch_hint`'s `other` dropped to `None`, which mypy accepts, a gap
killed; `deploy`'s first `started = None`, an equivalent mutant, as `None` is as false, refused by mypy once the flag is
annotated; and `Run.text`'s, dropped by a class-level declaration, not marked. The rerun with this change leaves 65 of
2261 mutants: 35 mypy refuses, 26 wording, 4 import, beside the 2 marked.

mutmut 3.8's operators, read in its `mutation/mutators.py`, decide what a restructure leaves: a call's argument is
replaced by `None` or dropped, unless it is starred (then only dropped); a list's elements are never dropped; `a = b`
becomes `a = None`, and `a = None` becomes `a = ""`; a string becomes `XX…XX` and its case-swapped self.

## Goals / Non-Goals

**Goals:** `commands/` with no survivor but known noise and two marked equivalents; the bug fixed.

**Non-Goals:** `cli` (its own change); testing message wording; changing what a user sees beyond the bug's message.
Moving `update` onto `review.running`, which would remove its parallel dry-run code at the root but change its dry-run
messages and hints: a change of its own, if wanted.

## Decisions

### Seams: each module's public functions

Tests go through `deploy.deploy`; `edit.add`, `remove`, `rename`, `bind`, `unbind`; `explain.show_why`, `tree_lines`,
`mermaid`, `link`, `repository`, `repositories`; `init_package.init`; `resolve.resolve`; `review.vendored`,
`check_target`, `fetch_hint`, `running`, `dry_cache` (below); `scope.of`; `transaction.pending`, `resolving`;
`update.update`; `vet.vet`. No test calls a `_private` function, as in `mutmut-infra`: `_undo_into`, `_write`,
`_remove`, `_ascii`, `_shown_edges`, `_quote`, `_path_url`, `_tip`, `_ls_remote`, `_keep_old`, `_restore` and
`_working_folder` are reached through these. Every module already has its test file; `scope.of` and `review.running` are
the seams of `_working_folder` and `Run`.

### The bug: a remote holding only tags

`_tip`, without `branch`, reads the remote's `HEAD`; when it names no branch, `ls-remote --heads` tells a remote with no
commits from one with no default branch. A remote holding only tags, its `HEAD` unborn, lists no heads, so `update` says
`the remote has no commits yet`, though it has, where the spec's **No default branch** scenario ("the remote's `HEAD`
names no existing branch") asks for an error suggesting a `branch` key. The fix asks for heads and tags,
`ls-remote --heads --tags`: either listed means commits exist, and the output stays bounded, where a bare `ls-remote`
would list a forge's every `refs/pull/*` only to see it is not empty. The scenario already covers it, so no delta spec;
a `Fixed` entry in `CHANGELOG.md` at archive. Test-first: `update` against a tag-only remote fails on the code, passes
after the fix; an empty remote keeps `no commits yet`.

### `review.dry_cache`: one dry-run cache, tested once

`review.Run.__init__` and `update.update` each build a dry run's cache: a `tempfile.TemporaryDirectory` with prefix
`skill-graft-` entered on an `ExitStack`, and a `Cache` over it falling back to `Cache.default()`. Their prefix mutants
(6) and `Run`'s `Cache(self.tmp, None)` (2) survive: nothing reads the folder's name, and a dry run that finds nothing
cached fetches anyway. One public function, `review.dry_cache(stack) -> Cache`, builds both, extracted in a refactor of
its own before any test; a caller needing the folder reads the cache's `root` (`Run.tmp` goes), and `Run` builds
`Cache.default()` only for a real run. Its test checks the root's name starts `skill-graft-`, that it is gone once the
stack closes, and that the cache's reference is the real one. `update` keeps its own flow (`--expect`, its flags),
calling it.

### Gaps, by module

- `review` (21, and `fetch_hint`'s `other` above): `vendored` with a lock of another version, a missing skills folder,
  an item with no `upstream`, and a hand-edited `sources` that is not a table, a source that is not a table, and a `ref`
  that is not a string; `fetch_hint` with a fetched skill holding two hidden lines and another skill after it, and
  keeping the other errors; `running`'s dry run that fails before `finish` prints no review hint (`Run.changed` starts
  false); `dry_cache` (above, with `update`'s three).
- `explain` (15): `tree_lines` with a rewritten prose edge before the edge that expands its target (`(*)` on the prose
  line), and a prose edge vendoring leaves alone followed by another edge (`continue`, not `break`); `repository` with a
  port that is no number; `repositories` with a skipped source (a path source, a non-forge URL, an unreadable cache
  repository) before a linked one, and a non-forge URL whose cache repository exists; `link`'s fragment decoded: no `=`
  left at its end, and its bytes those of `zlib.compress(state, 9)` on the same machine, not a pinned URL, as zlib-ng
  and Apple's zlib deflate differently and CI runs Linux and macOS; `mermaid` given a `Repository` whose name holds `"`,
  as no input of `tree` puts one in a label. And the survivors of the regex harness on `repository`'s regex, its new
  target (below): URLs whose user info holds a space, `\x01` or `\x7f`, which `urlsplit` keeps out of the host.
- `deploy` (13): `deploy --into` failing after its writes began leaves `into` empty. `transaction.resolving`'s
  `vendor.swap_back` removes `into/.apm/skills.new` and renames `skills.old` back before `_undo_into` runs, so the tests
  get past it: a `vendor.stage` patched to write `into/.apm/skills.new` and raise, as Ctrl-C mid-stage does (no swap
  yet, nothing swapped back); and a patched `lock.write` writing `into/skill-graft.lock`, `into/.apm/skills.old` and
  `skills.trash` and raising, with `vendor.swap_back` patched to fail as when its rename does, so each name reaches
  `_undo_into`. `test_interrupted`, whose interrupt hits the `resolve` run before `deploy`, so never reaches `into`,
  goes: the Ctrl-C mid-stage test replaces it.
- `edit` (12): the dry-run hint of `remove`, `rename`, `bind` and `unbind` names the command
  (`review: skill-graft remove … --dry-run --diff-file <file>`); `bind` and `unbind` with `--diff-file` write it;
  `remove` from a config with no `entries`. The hint follows a skill marked `+` or `~`, so the hint test changes a skill
  upstream first: a removal alone marks none.
- `vet` (9): `vet --into` of a skill with a nested file (`scripts/run.sh`) and a non-executable one: the folders made,
  modes exactly `0o755` and `0o644`; an `into` whose alias folder cannot be removed, after a failing print, raises the
  print's error, marked `needs_permissions` (the `owner_rights` fixture skips it as root and fails an unmarked chmod);
  file names holding `!` and `~` kept, not `?`.
- `update` (4, and the bug): `update a b --dry-run` prints `skill-graft update a b --dry-run --diff-file <file>`;
  `dry_cache`'s three (above).
- `transaction` (3): `pending` with no lock and a `skills.old` does not keep it; a caller's write whose new file is
  already gone at restore prints no `could not restore`.
- `resolve`, `init_package`, `scope` (1 each): a `resolve --diff-file` whose `explain.show` fails after the writes keeps
  the Deployed diff (`run.committed`); `init --project` failing with the package listed names the error; `scope.of` in a
  deleted working folder with `PWD` unset says `the working folder no longer exists`.

### Equivalent mutants: dropped first, a pragma only where none can be

`CONTRIBUTING.md`'s rule: remove what an equivalent mutant shows redundant, or restructure so none exists, or name the
value in a module-level constant; only then the equivalent expression alone on a line of its own, a bare
`# pragma: no mutate` on it, `# Equivalent mutants: <reason>` above. No regions.

**Removed, redundant (16):**

- `dry_run=False` on `resolve`, `add`, `remove`, `rename`, `bind`, `unbind`, `update`, and `project=False` on `init`:
  `cli.main` passes each, and no test leaves it out.
- `transaction.resolving`'s `checked` (5 with its two callers' mutants): `deploy --into`'s folder is checked empty
  first, so its copies' check finds none; `update` checks the same copies against the same lock before any remote, and
  `resolving` checks them again after the fetches: the same answer unless a copy was edited meanwhile, which the second
  check then refuses, as it should. `resolving` always checks; `test_checked_skips_the_check` goes, and the tests
  passing `checked=True` either drop it or start from copies the lock records.
- `missing_ok=True` in `_undo_into`'s unlink: `contextlib.suppress(OSError)` around it swallows the `FileNotFoundError`.
- `Run.text = ""` in `__init__`: `text: str` declared on the class instead. `stage` sets it wherever `finish` reads it,
  and a later caller of `finish` without `stage` raises `AttributeError` rather than writing an empty diff, which the
  next run's `check_target` would refuse.

**Restructured (14):**

- `explain.repository`: the control-character regex a module-level compiled constant, `_UNSAFE_URL` (`\x1f` and `\x1F`
  are one escape), added to `mutation/targets.py` (with `explain` in its `MODULES`) as the regex harness's target, since
  mutmut no longer reaches it and it keeps a token in a query out of the mermaid.live link; a URL without a host returns
  `None` at once, not through `or ""`, whose `"XXXX"` is no forge either; the segment count checked as
  `len(segments) < forge.segments or (not forge.deeper and len(segments) > forge.segments)`, whose mutants each change
  an accepted count, where `>` and `>=` were one after the `==`.
- `explain._path_url`: `quote(part)` without `safe=''`; a part of `Path.parts` never holds `/`, the one character the
  default keeps.
- `review.fetch_hint`: each hidden line paired with the next one's skill, the last with none:
  `zip(error.hidden, [*(s for s, _ in error.hidden[1:]), None])`, not a slice `[i + 1 : i + 2]` whose `i + 3` reads the
  same one element.
- `review.vendored`: `SkillId(*config.split_id(item["id"]))`, the split `lock.recorded` already makes, not an inline
  `partition("/")` whose `rpartition` reads a two-part ID alike.
- `update._tip`'s three `ls-remote` calls through one `_ls_remote(context, options, url, patterns)`, `options` and
  `patterns` lists without defaults, which builds `["ls-remote", *options, "--", url, *patterns]` and returns each
  line's two fields: `--`, `HEAD` and `refs/heads/<branch>` are list elements, which mutmut never drops, and a dropped
  argument is a `TypeError`; one parse where there were two (6).
- `update._update`'s `diff = ""`: the target and its text become one value,
  `written = None if target is None else (target, review.deployed_diff(…))`, read where the target was; nothing is left
  unbound for pyright's `reportPossiblyUnbound`, and no initial text stands in for one never built.
- `deploy`'s `started` annotated `bool`, with a comment saying why: its first `= None` mutant acts as `False`, and the
  annotation makes mypy refuse it.

**Marked (2):** each the expression alone on its line.

- `_ls_remote`'s `line.partition("\t")` (2 before, one line now): an `ls-remote` line holds one tab, and a ref name no
  control character, so `rpartition` splits it alike.
- `review.check_target`'s read of the first line's length: reading the whole file starts the same; the read moves to a
  line of its own, the length a module-level constant.

## Risks / Trade-offs

- \[`resolving` without `checked` hashes `update`'s copies twice\] → the copies are text files a few hundred KiB at
  most; one less parameter, and its test, outweighs it. Kept instead, it would need a pragma on `deploy`'s `checked=`
  line, which holds a mutant the tests kill.
- \[Patching `vendor.swap_back` in `deploy`'s test pins how `resolving` undoes a swap\] → only so the names `_undo_into`
  removes reach it; the test without the patch, Ctrl-C mid-stage, needs none.
- [The fix changes a message a user sees] → only for a remote holding tags but no default branch, which the spec already
  says to report so; an empty remote keeps its message.
- \[`link`'s test kills the `rstrip("XX=XX")` mutant only where a fragment ends in `X`\] → it runs 160 diagrams, one of
  them so on Linux's zlib; on another zlib the test still passes, the kill unchecked there.
- \[The regex harness finds more on `_UNSAFE_URL` than mutmut did\] → each survivor gets a test in `explain`'s task, or
  an entry in `mutation/equivalent.toml` with its reason.

## Migration Plan

None: tests, source changes that keep what a user sees, and the bug's message.

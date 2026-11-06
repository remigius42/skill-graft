# Tasks

Test-first: each task's test fails before its code, then passes. One commit per task. A task adding **Skills** commits
their labels, decided by design.md's rule, before any eval run of them; their record comes from `vet`. No task runs
`evals/`.

## 1. Payloads, triggers, injections and twins (`evals/graft-vet/corpus.py`, `tests/cli/test_vet_corpus.py`)

- [x] 1.1 `Place` (with `whole`), `Payload` (categories, core, triggers, twin), `Injection` (marker), `Skill.payloads`,
  `injections`, `attacks` (`-` for the existing), `labels` as each core place in each category, each trigger `run` and
  each injection `permission`; the existing **Skills** converted, one payload per harm (`quiet-step` two, upload `send`
  and keeping it from the user `permission`, no injection), `one-liner`'s "Run setup.sh" and `blob`'s "Decode" lines
  triggers, `blob`'s `data.txt` place `whole`, the fixed `INJECTION` lines injections, no twin for `injected-prose` or
  `injected-run`; the label rule in the module docstring; verify every existing **Skill**'s `labels` set unchanged, the
  record test passing, and new tests: places within their file and above line 0, every payload with a core place and a
  category, twins exist, hold no injection and their payload line is in the injected **Skill** verbatim, every injected
  **Skill** has an injection; replace `test_an_injection_is_labelled_permission` by every injection line labelled
  `permission`, each marker of letters and spaces only, and every corpus line holding a marker a line of that
  injection's text
- [x] 1.2 The corpus digest: SHA-256 over the whole corpus, names, kinds, attacks, files, payloads with their twins and
  injections, record left out; verify it changes with a label and not with the record

## 2. Score and compare

- [x] 2.1 `score <report> <skill folder> <transcript> <claude version> <model>`: per **Skill** the fixed key–value line
  of design.md (payloads by `reader` on a core place in one of their categories, `scan-only`, `missed`, triggers and
  injections flagged, `noise`, `line-0`, a `whole` place matched at line 0, `held`, `steered`, `unknown`, `no-reply`
  over twinned payloads, `status` last); per kind sums, `decoy`'s, `flood`'s and `line-zero`'s noise left out; `corpus`,
  `skill`, `claude`, `model` and `main-model` lines; verify spec scenarios "A payload caught on one of its lines", "A
  trigger alone", "A whole-file harm at line 0", "An injection steered its reader", "Twin missed too", "A reader with no
  reply", "Two payloads, two twins", and a `held`, on synthetic report files and transcripts, replacing the old
  `test_score`
- [x] 2.2 Subsets: `check <name>…` exits 2 naming an unknown name; `write <folder> [name…]` adds each twin of the named
  **Skills**' payloads; `score` covers the written **Skills**, prints `subset` and the whole corpus's digest; verify the
  twins added, the unknown name, `subset` and the digest equal to a full run's (added: `score` knows the written
  **Skills** as those with a status line in the report file, which the filter writes for every **Skill** it vetted; a
  full run whose report lacks a **Skill**'s status line scores as a `subset`)
- [x] 2.3 `compare <score>…`: sums per **Skill** and kind, run count, outcomes, a `subset` score out of the kind sums;
  exit 2 and no counts when `corpus`, `skill`, `claude` or `model` differ, naming which; verify "Runs on different
  labels", "Runs on different readers", a sum over two scores, and a subset summed with a full run
- [x] 2.4 `corpus.py injections`: each injection's marker, one per line; verify it lists every injected **Skill**'s

## 3. New Skills (labels first, then the record from `vet`)

- [x] 3.1 `injected-script` (naming `setup.sh`, never telling to run it), `injected-reference`, `injected-front-matter`,
  `injected-spread`, each payload twinned with `prose-fetch`; verify the record test, and that each holds
  `prose-fetch`'s payload line verbatim
- [x] 3.2 `split-lines`, `split-files` (`vars.sh` and `setup.sh`, no prose joining them), `pieces`, written to pass
  every pattern of `pipeline/vet.py`; verify the record test, and that the record holds no core line of them, the text
  rewritten before any run if it does
- [x] 3.3 `decoy` (twin `fetch-run`), `line-zero` and `flood` (one payload twinned with `fetch-run`, one with
  `prose-fetch`); verify the record test, "A decoy in the record", `flood`'s glossary times eight above 1000 lines
- [x] 3.4 `security-notes`, `token-words`, `never-pipe`, harmless, no labels, none running a shipped script or a
  destructive command; verify the record test
- [x] 3.5 `.cspell.yaml` words for the new **Skills**; verify the cspell hook passes (added: none needed for the
  **Skills** of 3.1, 3.3 and 3.4; 3.2's add their own with them)
- [x] 3.6 The mutation harness (`mutation/`): `mutation/targets.py` runs `tests/cli/test_vet_corpus.py` for every `vet`
  target, so the file keeps its name and its record test; verify `uv run python -m mutation` from the repository root
  exits 0, no new `survived` or `stale` line; a mutant listed in `mutation/equivalent.toml` that the larger corpus now
  kills leaves that file, in its own commit, `test(mutation): …` (added: run on the 34 `vet` targets alone, the only
  ones running the corpus test: 482 mutants, 474 killed, 8 equivalent, 0 survived; the corpus kills no listed mutant, so
  `equivalent.toml` stays)

## 4. The eval and its docs

- [x] 4.1 `run.sh corpus`: `CORPUS_SKILLS` checked by `corpus.py check` first, before the token check, and passed to
  `write`; no injection marker from `corpus.py injections` in the transcript, replacing the fixed phrase; `score` run
  with the report file, the project's `graft-vet` folder, the transcript, `claude --version` and
  `${ANTHROPIC_MODEL:-default}`, written to `score` beside the report file, both paths printed; `GRAFT_VET_SCORES`
  copying score and report as `<date>-<digest>-*`; verify `shellcheck` and `bash -n` pass, and "An unknown name"
- [x] 4.2 `evals/graft-vet/README.md`: the new score line, payloads, triggers and injections, twins and outcomes,
  `compare` and what it refuses, changing nothing else between runs to compare, the label rule and that labels precede
  runs; verify markdown hooks pass
- [x] 4.3 `docs/security.md` (graft-vet): one sentence on the properties the corpus attacks; verify markdown hooks pass

## 5. The skill, where the runs show it fails

- [x] 5.1 `skills/graft-vet/reader.json`: a line speaking to the reader as a reviewer, telling it what to reply, what to
  flag or not, or that the **Skill** is safe, is a place, `permission`, each line of it when spread; verify by
  `tests/cli/test_graft_vet.py`, spec scenario "Text addressed to the reviewer"
- [x] 5.2 Measure it (billed, run by the user):
  `CORPUS_SKILLS="injected-script injected-front-matter decoy line-zero flood"` with `GRAFT_VET_SCORES`, read per
  **Skill** against the two baseline scores; record the result in design.md
- [x] 5.3 `pieces`' payload `run` and `unreviewable`, in its own commit naming the runs and rule 1; verify by
  `tests/cli/test_vet_corpus.py`
- [x] 5.4 `skills/graft-vet/report-filter.sh`: a scan place also answered when the reader flagged its line in any
  category; `SKILL.md`, `docs/security.md` and the README say so; verify spec scenario "Same line, another category" by
  `tests/cli/test_graft_vet.py`, every other steering scenario still passing

## 6. Before archiving

- [x] 6.1 Bring proposal, design and spec in line with the code: names, score line, files; verify
  `openspec validate vet-corpus-adversarial` passes

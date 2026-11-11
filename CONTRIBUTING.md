# Contributing to dpcli

dpcli improves itself from real use. Most contributions start as *friction* an agent or a developer hit while working on a project, and arrive here as a pull request or an issue labelled `feedback`.

## The usual path: `dpcli contribute`

In a project that uses dpcli:

1. Frictions are logged as you work: `dp_feedback` in executor reports, `harness: …` notes by the coordinator and main session.
2. `dpcli feedback` groups them into clusters; `harness-retro` decides per cluster whether it is a **project** matter (fixed in the project's `.dpcli-local/`) or a **dpcli** matter.
3. A dpcli fix is made in the `.dpcli` submodule on a branch `improve/<F-n>-<slug>` (`dpcli contribute` makes it from uncommitted edits): a test reproducing the friction first, then the change and `changes/<F-n>-<slug>.md` with its CHANGELOG line (`- …`); `VERSION` and `CHANGELOG.md` stay untouched — the merge sets them.
4. `dpcli contribute F-n` opens the pull request — from `origin` if you can push, otherwise from your fork — or, if a similar one is already open, adds a `+1` with your evidence instead of a duplicate. No fix in `.dpcli` is a refusal; `--issue` reports without one on purpose.

Texts sent here are **anonymized**: no project names, paths, people or quotes — only what hurt, how often, and the proposed change.

## What happens to your PR

CI first merges current `main` into the PR (a conflict sends it back), then runs the tests and a budget check (size of agent prompts and code must not grow without a reason), then an AI reviewer posts `VERDICT: accept | rework | reject` with arguments. `accept` is merged; then `VERSION` + 1, the `changes/*.md` lines become the `## N` CHANGELOG section, and `vN` is tagged; every project picks it up on its next `dpcli update`. On `rework`, the next `dpcli update` in your project brings the arguments back so the fix can be reworked or dropped. Maintainers can always step in by hand. `metrics.py --write-budgets` only lowers `tools/budgets.json`; a justified raise is a hand edit explained in the PR.

## Manual contributions

Welcome as well. Before opening a PR:

- `python3 -m unittest discover -s tests` is green (Python ≥ 3.10, standard library only — no new dependencies);
- a test reproduces the problem you fix;
- `changes/<name>.md` has the CHANGELOG line; `VERSION` and `CHANGELOG.md` are untouched;
- command output stays terse: it is read by agents, every extra line is paid for in tokens;
- journals stay backward compatible: `events.jsonl` / `decisions.jsonl` are append-only, new fields are optional.

Smaller is better: a PR that removes code is reviewed with pleasure.

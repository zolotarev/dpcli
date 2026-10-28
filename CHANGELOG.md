# Changelog

## 6
- `dpcli feedback`: friction ledger from `dp_feedback`, `harness:` notes and review `harness`; dedup, clusters by topic, `new --match --scope project|dpcli`, `fix`, `wontfix`, `reopen`, `⚠N after fix` when a fixed friction comes back. Ledger in `.dpcli-local/feedback.jsonl`.
- `dpcli stats`: tasks, created→accepted, rework rounds, frictions per module; check durations (median/max) — `accept` now stores them.
- `dpcli contribute F-n`: a dpcli-scope fix as a PR to the hub from origin or a fork, a +1 on a similar open PR/issue, an issue without commits, or a patch when `gh` is unavailable. Anonymized bodies.
- `harness-retro` rebuilt on top of these; review template gets a `harness` field.

## 5
- Project layer `.dpcli-local/` (`local_dir`): `agents/<name>.append.md`, own agents and skills, project rules in the workflow and CLAUDE.md block; rendered by `init` on top of the distribution, survives updates.

## 4
- Everything in English: code, CLI output, agents, templates, docs. `language.text` / `language.commits` in the config choose the language agents write in and the language of commit messages.
- Repository presentation: CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, issue and PR templates.

## 3
- Layout: the repository root is the distribution; install into a project as the submodule `.dpcli` (`worktree.setup` initializes it in new copies).
- Agent models: coordinator and reviewer on sonnet (opus for the hardest reviews — at launch).
- `harness-retro` skill: process friction review and token cost measurement (`cost.py`); process changes only with the user's approval.
- Process: one session per phase/module, the main session does not poll on a timer, frictions logged as one-line `harness: …`.

## 2
- `deliver`, `area`, module base, worktree copy preparation (`worktree`), `protect_main`, `docs findings`, copies under `~/worktrees`.

# Changelog

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

# Changelog

## 22
- A `PreToolUse` hook (installed by `init`, delivered by `update`) refuses editing project files through Bash and points the agent to Edit/Write; programs, reads and temporary files pass. In the first project agents made ≈1200 such edits and no Edit calls; the v20 rule alone was not expected to change that.

## 21
- Reviewing work that lives in the main copy (a `--no-copy` card): `task brief` names the copy and branch where the work is instead of a copy that does not exist; `accept --here` checks the uncommitted changes against the scope instead of skipping it.
- Check logs are named by the check (`<log_dir>/<ID>/<check>.log`): with `--only` or re-created checks, stale logs of the same check stayed next to fresh ones under other numbers.
- `feedback --module/--since` lists only clusters that have frictions in that slice.

## 20
- Process rule: files are read and edited with the Read, Edit and Write tools, Bash runs programs (`rg`, `fd`, `jq`, `ast-grep`) — executors had edited files almost only through `python3 -`/`sed -i`/`cat >` heredocs.
- `install.sh --tools`: quiet non-interactive apt; a hint when `~/.local/bin` is not on PATH.

## 19
- `accept` warns when `git stash` is not empty: the stash is shared by all worktrees, and a pop in one copy took another task's changes (6 reports; the rule alone did not stop it).

## 18
- `task show` prints the "General rules" section of the process description; executor and reviewer prompts point there instead of the whole file (≈460 instead of ≈3300 tokens per task).
- A review stores the commit it looked at; after a rework `task brief --review` points the fresh reviewer to the previous issues and the diff since that commit only.
- One coordinator per wave: it reports `<m>: wave <n> done` and stops; the main session starts a fresh one (a growing context is paid on every turn).

## 17
- `accept` goes to the background by itself when its checks took longer than `checks.bg_after` (100 s) last time, and prints the wait command; `--fg` stays (21 reports: long foreground runs hit the agent's tool timeout).
- `task new|set --check-timeout NAME SEC`: a check's timeout in the card.
- `lock` runs in the foreground with its output by default; `--tmux` for a window (12 reports: output lost in a tmux job).
- Job names are per copy (`<copy>~<name>`): copies starting the same name no longer read each other's job (3 reports); jobs started before the update are still found by their old name.

## 16
- Scope checks no longer fail on files the card itself requires (25 reports): exclusions are `!pattern` entries in `scope`/`dont_touch`; prose like "src/api/ except a.py" is rejected at `task new`/`task set`; a scope path or glob directory inside `dont_touch` is rejected there too; files brought into the task branch by merges no longer count — the net diff restricted to the branch's own commits (accepted limitation: edits made while resolving a merge are not checked — `accept` says so when the branch has merges); `task new` lists test files that mention scope files so they can be added up front.

## 15
- `plan <m> <section>`: a section of several words needs no quotes; `5. Tasks / DS-0` and `4. Tasks (PF-5)` find the section by their most specific part; a card's `plan_ref` is checked at `task new` / `task set` (19 reports: "section from the card not found").
- `report <ID>` reads the per-task file `<log_dir>/<ID>/report.json` by default (brief and `task show` name it) and rejects a report whose `id` is another task's (13 reports: parallel agents overwrote a shared `/tmp/r.json`); a report without `id` is still accepted (old reports); explicit input (`FILE`, `< FILE`, `-` for a pipe) beats a stale per-task file; a pipe now needs `-` (an idle pipe in agent shells used to block); a report without `id` read from a file gets a warning.

## 14
- `install.sh`: no longer fails with `mv: cannot stat '.dpcli'` when `.dpcli` is recorded as a submodule without a `.gitmodules` entry (now registered and checked out) or when a vendored copy is tracked but deleted from disk (restored from the index first).

## 13
- Process description (`workflow.md`) trimmed by ~110 tokens more: duplicated and decorative phrases removed, no rule changed.

## 12
- Process description (`workflow.md`) trimmed by ~100 tokens: repeated and decorative phrases removed, no rule changed.

## 11
- `update` also commits the re-rendered process description (`workflow`, `.claude/dpcli-workflow.md` by default); it was left uncommitted when a release changed it.

## 10
- `task show` prints addenda in full (they were cut at 300 characters; executors missed instructions added after the brief); older than the last five — counted, shown with `--full`.

## 9
- `gc`: one `git status --ignored` per copy per run instead of one per (branch × copy) — 25 merged copies: 6.6 s → 0.9 s. Removed copies no longer block neighbours.
- Process rule: fast tools for agents (`rg`, `fd`, `jq`, `ast-grep`, Read with offset instead of `cat`/`sed -n`, scripts instead of long heredocs); `install.sh --tools` installs them.
- Measured on a real project and left as is (≤ 0.6 s): `status`, `status --since`, `search`, `docs find`, `docs check`, `feedback`.

## 8
- `install.sh`: installs or updates dpcli in an existing project (`curl … | bash`): submodule at the latest release, `language` (asked or `--lang` / `--commit-lang`), `worktree.setup`, `init`; migrates a vendored copy (own agents → `.dpcli-local/agents/`); `--tools` installs `rg`, `fd`, `jq`, `ast-grep`. Idempotent, never commits.

## 7
- `dpcli update [--auto] [--check] [--pin vN|--unpin] [--prs-only]`: moves the `.dpcli` submodule to the latest release tag, re-runs `init` with the project layer, commits the pointer and generated files, prints the new CHANGELOG lines; skips when `.dpcli` is dirty, on `improve/*`, has local commits, or offline.
- Checks own PRs/issues at the hub: merged → fixed; rework/rejected → reviewer arguments into the ledger.
- `init` adds the `SessionStart` hook `update --auto` (once a day).

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

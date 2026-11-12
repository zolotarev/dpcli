#!/usr/bin/env python3
"""Before the AI review: merge current main into the PR, so tests and review see what would land.
PRs leave VERSION and CHANGELOG.md to the merge (tools/decide.py bump), so any conflict is a real one.
A conflict, a fork branch or a merge the token cannot push (workflow files, without DPCLI_PUSH_TOKEN) → comment + `rework`, exit 1 (review skipped).
Runs from the base branch only: the merge happens in a separate worktree, nothing from the PR is executed.
shortcut: main moving during the review is not re-synced (decide.py's merge fails → `rework`, the next push
re-syncs); upgrade to a resync on push to main if that happens often."""
import base64
import json
import os
import subprocess
import sys

from decide import WORKFLOWS, gh, label


def git(*a, cwd=None, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a[:3])}: {r.stderr.strip()}")
    return r


def block(pr, why):
    gh("pr", "comment", pr, "--body", f"VERDICT: rework\n- Not reviewed: {why}.")  # update shows projects this line
    label(pr, "rework", ["rejected"])
    sys.exit(f"#{pr}: {why}")


def main(pr):
    info = json.loads(gh("pr", "view", pr, "--json", "headRefName,isCrossRepository"))
    head = f"refs/remotes/pr/{pr}"
    git("fetch", "-q", "origin", "main", f"+refs/pull/{pr}/head:{head}")
    if git("merge-base", "--is-ancestor", "origin/main", head, check=False).returncode == 0:
        return print(f"#{pr}: up to date with main")
    sha = git("rev-parse", head).stdout.strip()
    wt = os.path.join(os.environ.get("RUNNER_TEMP") or "/tmp", f"pr-{pr}")
    git("worktree", "add", "-q", "--detach", wt, head)
    git("-c", "merge.conflictStyle=merge", "merge", "-q", "--no-commit", "--no-ff", "origin/main", cwd=wt, check=False)
    conflicts = set(git("diff", "--name-only", "--diff-filter=U", cwd=wt).stdout.split())
    if conflicts:
        block(pr, f"conflicts with main in {', '.join(sorted(conflicts))}; merge main and push")
    if info["isCrossRepository"]:  # the workflow token cannot push to a fork; a clean one is tested on its merge ref
        return print(f"#{pr}: fork, merges cleanly with main; reviewed as is")
    auth = []  # the workflow token may not push a merge that brings workflow files; DPCLI_PUSH_TOKEN (workflows scope) may
    if git("diff", "--name-only", f"{head}...origin/main", "--", ".github/workflows").stdout.strip():
        tok = os.environ.get("PUSH_TOKEN")
        if not tok:
            block(pr, f"{WORKFLOWS} since this branch, and the CI token may not push workflow files; "
                      "merge main into the branch and push (not a conflict), or give CI a DPCLI_PUSH_TOKEN secret")
        h = "http.https://github.com/.extraheader"  # empty first: drop checkout's header, send only this one
        auth = ["-c", f"{h}=", "-c", f"{h}=AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{tok}".encode()).decode()]
    git("commit", "-q", "--no-edit", cwd=wt)
    b = info["headRefName"]
    r = git(*auth, "push", "-q", f"--force-with-lease=refs/heads/{b}:{sha}", "origin", f"HEAD:refs/heads/{b}", cwd=wt, check=False)
    if r.returncode:  # the author pushed meanwhile: that push starts a new review, which cancels this one
        sys.exit(f"#{pr}: push rejected ({r.stderr.strip()[-200:]}); the branch moved, its new review takes over")
    # a push with the workflow token starts no workflows: run the tests on the new head for decide.py
    gh("workflow", "run", "test.yml", "--ref", b, "-f", f"ref={b}")
    print(f"#{pr}: merged main")


if __name__ == "__main__":
    main(sys.argv[1])

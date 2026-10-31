#!/usr/bin/env python3
"""Before the AI review: merge current main into the PR, so tests and review see what would land.
Parallel PRs always collide on VERSION and the top of CHANGELOG.md: resolved here (the PR becomes main's VERSION + 1).
Any other conflict, or a fork branch behind main → comment + `rework`, exit 1 (the review is skipped).
Runs from the base branch only: the merge happens in a separate worktree, nothing from the PR is executed.
shortcut: main moving during the review is not re-synced (decide.py's merge fails, the PR stays open); upgrade to a
resync on push to main if that happens often."""
import json
import os
import re
import subprocess
import sys

from decide import gh, label
from pr_checks import DIST

INIT, LOG = "lib/dpcli/__init__.py", "CHANGELOG.md"
SECTION = re.compile(r"^## (\d+)[^\n]*\n(.*?)(?=^## \d|\Z)", re.M | re.S)


def git(*a, cwd=None, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a[:3])}: {r.stderr.strip()}")
    return r


def version(text):
    return int(re.search(r"^VERSION = (\d+)", text, re.M)[1])


def bumped(init, n):
    return re.sub(r"^VERSION = \d+", f"VERSION = {n}", init, count=1, flags=re.M)


def changelog(main_log, base_log, pr_log, n):
    """main's CHANGELOG with the PR's own lines (sections absent at the merge base) on top as section n."""
    own = [body.strip() for _n, body in SECTION.findall(pr_log) if body.strip() not in base_log]
    if not own:
        return main_log
    i = main_log.find("\n## ")
    i = len(main_log) if i < 0 else i + 1
    return main_log[:i] + f"## {n}\n" + "\n".join(own) + "\n\n" + main_log[i:]


def block(pr, why):
    gh("pr", "comment", pr, "--body", f"Not reviewed: {why}.")
    label(pr, "rework", ["rejected"])
    sys.exit(f"#{pr}: {why}")


def main(pr):
    info = json.loads(gh("pr", "view", pr, "--json", "headRefName,isCrossRepository"))
    head = f"refs/remotes/pr/{pr}"
    git("fetch", "-q", "origin", "main", f"+refs/pull/{pr}/head:{head}")
    if git("merge-base", "--is-ancestor", "origin/main", head, check=False).returncode == 0:
        return print(f"#{pr}: up to date with main")
    if info["isCrossRepository"]:  # the workflow token cannot push to a fork
        block(pr, "the branch is behind main and lives in a fork; merge main into it and push")
    wt = os.path.join(os.environ.get("RUNNER_TEMP") or "/tmp", f"pr-{pr}")
    git("worktree", "add", "-q", "--detach", wt, head)
    git("merge", "-q", "--no-commit", "--no-ff", "origin/main", cwd=wt, check=False)
    conflicts = set(git("diff", "--name-only", "--diff-filter=U", cwd=wt).stdout.split())
    files = git("diff", "--name-only", f"origin/main...{head}").stdout.split()
    dist = any(f.startswith(DIST) for f in files)
    if conflicts - ({INIT, LOG} if dist else set()):
        block(pr, f"conflicts with main in {', '.join(sorted(conflicts))}; merge main and push")
    if dist:
        show = lambda ref, f: git("show", f"{ref}:{f}").stdout
        base = git("merge-base", "origin/main", head).stdout.strip()
        n = version(show("origin/main", INIT)) + 1
        if conflicts or version(show(head, INIT)) != n:
            with open(os.path.join(wt, INIT), "w", encoding="utf-8") as f:
                f.write(bumped(show("origin/main", INIT), n))
            with open(os.path.join(wt, LOG), "w", encoding="utf-8") as f:
                f.write(changelog(show("origin/main", LOG), show(base, LOG), show(head, LOG), n))
    git("add", "-A", cwd=wt)
    git("commit", "-q", "--no-edit", cwd=wt)
    b = info["headRefName"]
    if git("push", "-q", "origin", f"HEAD:refs/heads/{b}", cwd=wt, check=False).returncode:
        block(pr, "could not push the merge with main (workflow files changed?); merge main and push")
    # a push with the workflow token starts no workflows: run the tests on the new head for decide.py
    gh("workflow", "run", "test.yml", "--ref", b, "-f", f"ref={b}")
    print(f"#{pr}: merged main" + (f", VERSION {n}" if dist else ""))


if __name__ == "__main__":
    main(sys.argv[1])

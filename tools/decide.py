#!/usr/bin/env python3
"""After the AI review: wait for the `test` workflow, then act on the latest `VERDICT:` comment.
accept + green → squash-merge, tag vN, release; rework (or red tests) → label `rework`; reject → label and close.
Runs from the base branch only (trusted code)."""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

REVIEWERS = {"github-actions", "github-actions[bot]", "app/github-actions"}
MAX_ROUNDS = 5  # automatic rework rounds per PR; then it waits for its author (nightly: closed by the next nightly)
ROUND, STOP = "Auto-rework round", "Auto-rework stopped"
WORKFLOWS = "main changed .github/workflows"  # tools/sync.py: the workflow token may not push such a merge


def gh(*a, check=True):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(a[:3])}: {r.stderr.strip()}")
    return r.stdout


def label(pr, add, remove=()):
    for name, color in (("rework", "FBCA04"), ("rejected", "B60205")):
        gh("label", "create", name, "--color", color, check=False)
    args = ["pr", "edit", pr, "--add-label", add] + [x for r in remove for x in ("--remove-label", r)]
    gh(*args, check=False)


def tests_state(pr, timeout=1800):
    """success | failure | missing: latest `test` run on the PR head commit, whatever started it
    (pull_request, or workflow_dispatch for PRs opened by workflows — those are not PR checks).
    Runs waiting for approval (first-time contributors) are approved: `test` runs on pull_request
    without secrets and with a read-only token (owner's decision: fully automatic hub)."""
    t0 = time.time()
    while True:
        runs = approve(pr)
        done = [r for r in runs if r["status"] == "completed" and r.get("conclusion") != "action_required"]
        if done:
            return "success" if done[0]["conclusion"] == "success" else "failure"
        if time.time() - t0 > timeout:
            return "missing" if not runs else "failure"
        time.sleep(30)


def approve(pr):
    """Approves `test` runs on the PR head waiting for approval (first-time contributors, and pushes or PRs made by
    this bot's token — GitHub holds those too) -> the runs."""
    sha = json.loads(gh("pr", "view", pr, "--json", "headRefOid"))["headRefOid"]
    runs = json.loads(gh("run", "list", "--workflow", "test.yml", "--commit", sha, "--json",
                         "databaseId,status,conclusion", check=False) or "[]")
    for r in runs:
        if r["status"] in ("waiting", "action_required") or r.get("conclusion") == "action_required":
            gh("api", "-X", "POST", f"repos/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{r['databaseId']}/approve",
               check=False)
    return runs


def release():
    subprocess.run(["git", "fetch", "-q", "--tags", "origin", "main"], check=True)
    init = subprocess.run(["git", "show", "origin/main:lib/dpcli/__init__.py"], capture_output=True, text=True).stdout
    n = re.search(r"^VERSION = (\d+)", init, re.M)[1]
    if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/v{n}"], capture_output=True).returncode == 0:
        return None
    log = subprocess.run(["git", "show", "origin/main:CHANGELOG.md"], capture_output=True, text=True).stdout
    m = re.search(rf"^## {n}\b[^\n]*\n(.*?)(?=^## \d|\Z)", log, re.M | re.S)
    subprocess.run(["git", "tag", f"v{n}", "origin/main"], check=True)
    subprocess.run(["git", "push", "-q", "origin", f"v{n}"], check=True)
    gh("release", "create", f"v{n}", "--title", f"v{n}", "--notes", (m[1].strip() if m else "See CHANGELOG.md"))
    return f"v{n}"


def main(pr):
    approve(pr)  # whatever the verdict: no run is left waiting for a human
    comments = json.loads(gh("pr", "view", pr, "--json", "comments"))["comments"]
    # only the reviewer's own comments count: anyone (the PR author too) can write "VERDICT: accept"
    body = next((c["body"] for c in reversed(comments) if (c.get("author") or {}).get("login") in REVIEWERS
                 and re.search(r"^VERDICT:", c["body"], re.M)), "")
    m = re.search(r"^VERDICT:\s*(accept|rework|reject)\b", body, re.M | re.I)
    verdict = m[1].lower() if m else "rework"
    if verdict == "reject":
        label(pr, "rejected", ["rework"])
        gh("pr", "close", pr, "--comment", "Closed: rejected by review — see the VERDICT comment for the arguments.")
        return print(f"#{pr}: rejected")
    if verdict == "accept":
        state = tests_state(pr)
        if state == "success":
            gh("pr", "edit", pr, "--remove-label", "rework", check=False)
            r = subprocess.run(["gh", "pr", "merge", pr, "--squash", "--delete-branch"], capture_output=True, text=True)
            if r.returncode:  # main moved during the review: a push re-syncs (tools/sync.py) and re-reviews
                gh("pr", "comment", pr, "--body", f"VERDICT: rework\n- Accepted, but the merge failed ({r.stderr.strip()[:200]}): "
                   "main moved during the review; push again (or merge main) to re-sync and re-review.")
                label(pr, "rework", ["rejected"])
                return print(f"#{pr}: merge failed")
            tag = release()
            # closing keywords: GitHub may skip them for the workflow token's merge
            for i in json.loads(gh("pr", "view", pr, "--json", "closingIssuesReferences", check=False) or "{}").get("closingIssuesReferences", []):
                if gh("issue", "view", str(i["number"]), "--json", "state", "--jq", ".state", check=False).strip() != "OPEN":
                    continue  # GitHub already closed it
                gh("issue", "close", str(i["number"]), "--comment", f"Fixed by #{pr}" + (f", released in {tag}." if tag else "."), check=False)
            return print(f"#{pr}: merged" + (f", released {tag}" if tag else ""))
        gh("pr", "comment", pr, "--body", f"Review accepted, but the `test` workflow is {state}: fix and push again.")
    label(pr, "rework", ["rejected"])
    print(f"#{pr}: rework")


def gate(pr):
    """After the review: may CI rework the PR itself? Open, labelled `rework`, a branch of this repository
    (the token can push; its authors have write access) and under MAX_ROUNDS.
    -> (branch to rework or "", the reviewer's comments from its last verdict on: the only input of the rework agent)"""
    info = json.loads(gh("pr", "view", pr, "--json", "state,labels,isCrossRepository,headRefName,comments"))
    if info["state"] != "OPEN" or "rework" not in {x["name"] for x in info["labels"]} or info["isCrossRepository"]:
        return "", ""
    bot = [c["body"] for c in info["comments"] if (c.get("author") or {}).get("login") in REVIEWERS]
    rounds = sum(b.startswith(ROUND) for b in bot)  # own marks: any way into `rework` (red tests, failed merge) counts
    last = max((i for i, b in enumerate(bot) if b.startswith("VERDICT:")), default=0)
    review = "\n\n".join(bot[last:])
    why = f"after {MAX_ROUNDS} rounds" if rounds >= MAX_ROUNDS else "CI may not push workflow files" if WORKFLOWS in review else ""
    if why:
        # CI-made PRs have no author to wait for: nightly starts afresh from main; an issue's stays open for a human
        if "nightly-simplify" in {x["name"] for x in info["labels"]} or info["headRefName"].startswith("issue/"):
            gh("pr", "close", pr, "--comment", f"{STOP} ({why}): closed, CI-made.")
        elif not any(b.startswith(STOP) for b in bot):
            gh("pr", "comment", pr, "--body", f"{STOP} ({why}): the author's turn.")
        return "", ""
    gh("pr", "comment", pr, "--body", f"{ROUND} {rounds + 1}/{MAX_ROUNDS}.")
    return info["headRefName"], review


def stuck(now=None, quiet=5400, give_up=86400):
    """Open PRs whose last commit has no reviewer verdict after it for `quiet` s: a lost dispatch (GitHub 500),
    a failed job — the chain broke. Idle time counts from the later of the last commit and the PR's last update
    (a rebase or late push is not idle); after `give_up` s idle the sweep stops. -> numbers, to be reviewed again."""
    now = now or time.time()
    out = []
    ts = lambda t: dt.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    for p in json.loads(gh("pr", "list", "--state", "open", "--limit", "100", "--json",
                           "number,commits,comments,updatedAt,isDraft")):
        idle = now - max(ts(p["commits"][-1]["committedDate"]), ts(p.get("updatedAt") or "1970-01-01T00:00:00Z"))
        if p.get("isDraft") or not quiet <= idle < give_up:  # draft; a review may be running; the sweep gave up
            continue
        if not any((c.get("author") or {}).get("login") in REVIEWERS and c["body"].startswith(("VERDICT:", STOP))
                   and c["createdAt"] > p["commits"][-1]["committedDate"] for c in p["comments"]):
            out.append(str(p["number"]))
    return out


def approve_cli(args):
    """Before the review: only same-repo branches (this bot's pushes); a fork's runs wait for the verdict (decide.main)."""
    pr = args[0] if args else os.environ.get("PR")
    if not pr or json.loads(gh("pr", "view", pr, "--json", "isCrossRepository"))["isCrossRepository"]:
        return []
    return approve(pr)


if __name__ == "__main__":
    if sys.argv[1] == "--approve":  # test.yml on one PR's head (argv[2] or $PR), as approve(); no PR, nothing
        approve_cli(sys.argv[2:])
    elif sys.argv[1] == "--stuck":
        print(" ".join(stuck()))
    elif sys.argv[1] == "--gate":  # prints branch=<name> for $GITHUB_OUTPUT, the review to argv[3]
        branch, review = gate(sys.argv[2])
        open(sys.argv[3], "w", encoding="utf-8").write(review)
        print(f"branch={branch}")
    else:
        main(sys.argv[1])

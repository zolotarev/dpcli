#!/usr/bin/env python3
"""After the AI review: wait for the `test` workflow, then act on the latest `VERDICT:` comment.
accept + green → squash-merge, tag vN, release; rework (or red tests) → label `rework`; reject → label and close.
Runs from the base branch only (trusted code)."""
import json
import re
import subprocess
import sys
import time

REVIEWERS = {"github-actions", "github-actions[bot]", "app/github-actions"}


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
    """success | failure | missing, waiting for the `test` workflow on the PR head."""
    t0 = time.time()
    while True:
        checks = json.loads(gh("pr", "checks", pr, "--json", "name,state,workflow", check=False) or "[]")
        mine = [c for c in checks if c.get("workflow") == "test"]
        if mine and all(c["state"] not in ("PENDING", "QUEUED", "IN_PROGRESS") for c in mine):
            return "success" if all(c["state"] in ("SUCCESS", "SKIPPED", "NEUTRAL") for c in mine) else "failure"
        if time.time() - t0 > timeout:
            return "missing" if not mine else "failure"
        time.sleep(30)


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
            gh("pr", "merge", pr, "--squash", "--delete-branch")
            tag = release()
            return print(f"#{pr}: merged" + (f", released {tag}" if tag else ""))
        gh("pr", "comment", pr, "--body", f"Review accepted, but the `test` workflow is {state}: fix and push again.")
    label(pr, "rework", ["rejected"])
    print(f"#{pr}: rework")


if __name__ == "__main__":
    main(sys.argv[1])

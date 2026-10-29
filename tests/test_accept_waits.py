"""Frictions: long accept blocks the agent; check timeout not settable; lock output lost in tmux; job names collide."""
import json
import unittest

from helpers import Project, git


class AcceptWithoutWaits(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.addCleanup(self.p.cleanup)
        self.p.ok("module", "init", "aa", "--code", "AA")
        self.p.ok("task", "new", "aa", "--type", "dp-writer", "--title", "T", "--scope", "src",
                  "--check", "slow", "true", "exit=0", "--check-timeout", "slow", "5", "--no-copy")

    def test_check_timeout_in_card(self):
        card = json.loads(self.p.ok("task", "show", "AA-1", "--json"))
        self.assertEqual(card["accept"][0]["timeout"], 5)
        self.p.ok("task", "set", "AA-1", "--check-timeout", "slow", "7")
        self.assertEqual(json.loads(self.p.ok("task", "show", "AA-1", "--json"))["accept"][0]["timeout"], 7)

    def test_known_long_accept_goes_to_background(self):
        res = self.p.root / "build" / "dpcli" / "AA-1" / "results.json"
        res.parent.mkdir(parents=True, exist_ok=True)
        res.write_text(json.dumps({"slow": {"ok": True, "val": "exit 0", "t": "2026-01-01T00:00:00", "head": "x", "dur": 500}}))
        out = self.p.ok("accept", "AA-1", "--dry")
        self.assertIn("background", out)
        self.assertIn("job wait dp-accept-AA-1", out)
        self.assertIn("PASS slow", self.p.ok("job", "wait", "dp-accept-AA-1", "60"))
        self.assertIn("PASS slow", self.p.ok("accept", "AA-1", "--dry", "--fg"))

    def test_lock_runs_in_foreground_with_output(self):
        out = self.p.ok("lock", "cpu", "t", "--", "echo", "hello-from-lock", env={"DPCLI_NO_TMUX": ""})
        self.assertIn("hello-from-lock", out)

    def test_job_names_are_per_copy(self):
        copy = self.p.copies / "other"
        git("worktree", "add", "-q", "-b", "x", str(copy), "main", cwd=self.p.root)
        self.p.ok("job", "start", "acc", "30", "--", "true")
        self.p.ok("job", "start", "acc", "30", "--", "true", cwd=copy)
        self.p.ok("job", "wait", "acc", "30")
        self.p.ok("job", "wait", "acc", "30", cwd=copy)
        status = self.p.ok("job", "status", "--all")
        self.assertEqual(status.count("acc:"), 2, status)


if __name__ == "__main__":
    unittest.main()

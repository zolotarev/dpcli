"""Frictions: false scope failures — free text in paths, scope inside dont_touch, files brought by merges,
tests the change breaks but the card does not list."""
import unittest

from helpers import Project, git


class HonestScope(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.addCleanup(self.p.cleanup)
        self.p.ok("module", "new", "aa", "--code", "AA")
        self.mc = self.p.copies / "proj" / "aa"

    def task(self, *extra, ok=True):
        args = ("task", "new", "aa", "--type", "dp-writer", "--title", "T", "--check", "c", "true", "exit=0", *extra)
        if not ok:
            return self.p.run(*args, cwd=self.mc)
        tid = self.p.ok(*args, cwd=self.mc).split(":")[0]
        return tid, self.p.copies / "proj" / f"aa-{tid}"

    def write(self, tc, path):
        f = tc / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")
        self.p.commit_all(path, cwd=tc)

    def test_free_text_exclusion_rejected(self):
        code, _, err = self.task("--scope", "src/", "--dont-touch", "src/api/ кроме a.py", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("!<path>", err)

    def test_scope_inside_dont_touch_rejected_then_exclusion_works(self):
        code, _, err = self.task("--scope", "src/api/a.py", "--dont-touch", "src/api/", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("dont_touch", err)
        tid, tc = self.task("--scope", "src/api/a.py", "--dont-touch", "src/api/", "--dont-touch", "!src/api/a.py")
        self.write(tc, "src/api/a.py")
        code, out, _ = self.p.run("accept", tid, cwd=tc)
        self.assertEqual(code, 0, out)
        self.write(tc, "src/api/b.py")
        code, out, _ = self.p.run("accept", tid, cwd=tc)
        self.assertEqual(code, 1, out)
        self.assertIn("src/api/b.py", out)

    def test_files_brought_by_a_merge_are_not_the_tasks(self):
        tid, tc = self.task("--scope", "src/")
        self.write(tc, "src/a.py")
        git("switch", "-q", "-c", "side", "aa/" + tid, cwd=tc)
        self.write(tc, "other/foreign.py")
        git("switch", "-q", "aa/" + tid, cwd=tc)
        git("merge", "-q", "--no-ff", "-m", "merge side", "side", cwd=tc)
        code, out, _ = self.p.run("accept", tid, cwd=tc)
        self.assertEqual(code, 0, out)

    def test_hint_tests_referencing_scope_files(self):
        f = self.mc / "src" / "billing.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        t = self.mc / "tests" / "test_billing_totals.py"
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text("from src import billing\n")
        self.p.commit_all("code", cwd=self.mc)
        out = self.p.ok("task", "new", "aa", "--type", "dp-writer", "--title", "T", "--check", "c", "true", "exit=0",
                        "--scope", "src/billing.py", cwd=self.mc)
        self.assertIn("tests/test_billing_totals.py", out)


if __name__ == "__main__":
    unittest.main()

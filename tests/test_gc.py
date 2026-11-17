"""gc: a merged copy that another copy links into is skipped; the scan is one git status per copy."""
import os
import unittest

from helpers import Project, git


class Gc(unittest.TestCase):
    def test_symlinked_copy_skipped(self):
        p = Project()
        self.addCleanup(p.cleanup)
        r = p.root
        (r / ".gitignore").write_text("node_modules/\n")
        p.commit_all("ignore")
        a, b = p.copies / "a", p.copies / "b"
        for name, path in (("ta", a), ("tb", b)):
            git("worktree", "add", "-q", "-b", name, str(path), "main", cwd=r)
            (path / f"{name}.txt").write_text(name)
            git("add", f"{name}.txt", cwd=path)
            git("commit", "-q", "-m", name, cwd=path)
            git("merge", "-q", "--no-ff", "-m", f"m {name}", name, cwd=r)
        (a / "node_modules").mkdir()
        os.symlink(a / "node_modules", b / "node_modules")
        out = p.ok("gc")
        self.assertRegex(out, r"skip ta .*symlinks from other copies")
        self.assertIn("tb @", out)

    def test_squash_merged(self):
        """A branch squash-merged into main (and a branch merged into it) is removable; an unmerged one is not."""
        p = Project()
        self.addCleanup(p.cleanup)
        r = p.root
        mod, task = p.copies / "mod", p.copies / "task"
        git("worktree", "add", "-q", "-b", "fm", str(mod), "main", cwd=r)
        git("worktree", "add", "-q", "-b", "fm-t", str(task), "fm", cwd=r)
        (task / "t.txt").write_text("t")
        p.commit_all("t", cwd=task)
        git("merge", "-q", "--no-ff", "-m", "m t", "fm-t", cwd=mod)
        (mod / "j.txt").write_text("j")
        p.commit_all("j", cwd=mod)
        git("branch", "other", "main", cwd=r)
        (r / "o.txt").write_text("o")
        p.commit_all("o")  # main moves on before the squash
        git("merge", "-q", "--squash", "fm", cwd=r)
        git("commit", "-q", "-m", "squash fm", cwd=r)
        git("checkout", "-q", "other", cwd=r)
        (r / "x.txt").write_text("x")
        p.commit_all("x")
        git("checkout", "-q", "main", cwd=r)
        out = p.ok("gc", "--remove")
        self.assertIn("removed fm @", out)
        self.assertIn("removed fm-t @", out)
        self.assertNotIn("other", out)
        self.assertNotIn("fm", git("branch", "--format=%(refname:short)", cwd=r).split())

    def _pay(self, **kw):
        """Module pay delivered via a review branch: archive/pay at feature/pay, task branch pay/PY-1 inside it."""
        p = Project(**kw)
        self.addCleanup(p.cleanup)
        r = p.root
        mod, task = p.copies / "pay", p.copies / "pay-PY-1"
        git("worktree", "add", "-q", "-b", "feature/pay", str(mod), "main", cwd=r)
        git("worktree", "add", "-q", "-b", "pay/PY-1", str(task), "feature/pay", cwd=r)
        (task / "t.txt").write_text("t")
        p.commit_all("t", cwd=task)
        git("merge", "-q", "--no-ff", "-m", "m t", "pay/PY-1", cwd=mod)
        git("tag", "archive/pay", "feature/pay", cwd=r)
        return p, r, mod, task

    def test_archived_module_removable(self):
        """The module branch at its archive tag and its task branch are removed, the tag stays as the recovery point;
        a module branch without a tag is kept."""
        p, r, _, _ = self._pay()
        git("branch", "feature/draft", "main", cwd=r)
        git("checkout", "-q", "feature/draft", cwd=r)
        (r / "d.txt").write_text("d")
        p.commit_all("d")
        git("checkout", "-q", "main", cwd=r)
        out = p.ok("gc", "--remove")
        self.assertIn("removed feature/pay @", out)
        self.assertIn("removed pay/PY-1 @", out)
        self.assertIn("kept by tag archive/pay", out)
        left = git("branch", "--format=%(refname:short)", cwd=r).split()
        self.assertNotIn("feature/pay", left)
        self.assertIn("feature/draft", left)
        self.assertEqual(git("tag", "-l", "archive/pay", cwd=r).strip(), "archive/pay")

    def test_archived_task_outside_tag_kept_explicit_arg(self):
        """A task branch with a commit outside the tag is kept; `gc pay` names the module explicitly."""
        p, r, mod, task = self._pay()
        (task / "x.txt").write_text("x")
        p.commit_all("outside", cwd=task)
        out = p.ok("gc", "--remove", "pay")
        self.assertIn("removed feature/pay @", out)
        left = git("branch", "--format=%(refname:short)", cwd=r).split()
        self.assertNotIn("feature/pay", left)
        self.assertIn("pay/PY-1", left)

    def test_archived_tag_disabled_or_module_moved(self):
        """deliver.archive_tag empty: nothing matched. Module branch moved past its tag: kept."""
        p, r, _, _ = self._pay(config={"deliver": {"archive_tag": ""}})
        self.assertNotIn("feature/pay", p.ok("gc", "--remove"))
        p, r, mod, _ = self._pay()
        (mod / "more.txt").write_text("more")
        p.commit_all("more", cwd=mod)
        p.ok("gc", "--remove")
        self.assertIn("feature/pay", git("branch", "--format=%(refname:short)", cwd=r).split())

    def test_squash_then_more_work_and_empty_diff_kept(self):
        """Kept: a branch with a commit after its squash, and a branch whose net diff is empty."""
        p = Project()
        self.addCleanup(p.cleanup)
        r = p.root
        git("checkout", "-q", "-b", "more", cwd=r)
        (r / "a.txt").write_text("a")
        p.commit_all("a")
        git("checkout", "-q", "main", cwd=r)
        git("merge", "-q", "--squash", "more", cwd=r)
        git("commit", "-q", "-m", "squash more", cwd=r)
        git("checkout", "-q", "more", cwd=r)
        (r / "b.txt").write_text("b")
        p.commit_all("b")  # work after the squash
        git("checkout", "-q", "-b", "empty", "main", cwd=r)
        (r / "e.txt").write_text("e")
        p.commit_all("e")
        (r / "e.txt").unlink()
        p.commit_all("revert e")  # tree == merge-base tree
        git("checkout", "-q", "main", cwd=r)
        out = p.ok("gc", "--remove")
        self.assertIn("no merged branches", out)
        self.assertTrue({"more", "empty"} <= set(git("branch", "--format=%(refname:short)", cwd=r).split()))


if __name__ == "__main__":
    unittest.main()

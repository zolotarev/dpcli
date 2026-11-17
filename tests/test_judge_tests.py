import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from dpcli.commands import accept  # noqa: E402

VITEST = (r"^\s*Tests\s+(?:(?P<failed>\d+) failed)?(?:\s*\|\s*)?(?:(?P<passed>\d+) passed)?"
          r"(?:\s*\|?\s*(?P<skipped>\d+) (?:skipped|todo))*\s*\((?P<total>\d+)\)")


def judge(out, rx=VITEST):
    with mock.patch.object(accept.config, "get", lambda k, d=None: rx if k == "checks.tests_summary" else d):
        return accept.judge({"tests": True}, 0, out)


class JudgeTests(unittest.TestCase):
    def test_filter_matching_nothing_fails(self):
        # a test-name filter that matches no test: the runner skips everything and exits 0
        ok, val = judge("      Tests  2686 skipped (2686)\n")
        self.assertFalse(ok, val)

    def test_passed_run_passes(self):
        self.assertTrue(judge("      Tests  33 passed | 2 todo (35)\n")[0])

    def test_failed_run_fails(self):
        self.assertFalse(judge("      Tests  1 failed | 33 passed (34)\n")[0])

    def test_default_summary_without_passed_group(self):
        self.assertTrue(judge("5 tests, 0 failed\n", accept.TESTS_SUMMARY)[0])
        self.assertFalse(judge("0 tests, 0 failed\n", accept.TESTS_SUMMARY)[0])


if __name__ == "__main__":
    unittest.main()

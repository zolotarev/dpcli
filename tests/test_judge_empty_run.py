import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from dpcli.commands import accept  # noqa: E402


def judge(out, cfg=None):
    with mock.patch.object(accept.config, "get", lambda k, d=None: (cfg or {}).get(k, d)):
        return accept.judge({"exit": 0}, 0, out)


class JudgeEmptyRun(unittest.TestCase):
    def test_package_filter_matching_nothing_fails(self):
        # a wrong package name in `pnpm --filter X build`: nothing is built and pnpm exits 0
        ok, val = judge("No projects matched the filters in \"/repo\"\n")
        self.assertFalse(ok, val)
        self.assertIn("ran nothing", val)

    def test_real_build_passes(self):
        self.assertTrue(judge("Scope: 2 of 30 workspace projects\nbuild: Done\n")[0])

    def test_pattern_from_config(self):
        self.assertFalse(judge("collected 0 items\n", {"checks.empty_run": r"collected 0 items"})[0])
        self.assertTrue(judge("No projects matched the filters\n", {"checks.empty_run": r"collected 0 items"})[0])

    def test_invalid_regex_is_dp_error(self):
        with self.assertRaises(accept.DpError):
            judge("x\n", {"checks.empty_run": "("})

    def test_empty_string_disables(self):
        self.assertTrue(judge("No projects matched the filters\n", {"checks.empty_run": ""})[0])

    def test_skipped_when_expect_tests_output(self):
        with mock.patch.object(accept.config, "get", lambda k, d=None: None):
            ok, _ = accept.judge({"re": "No projects matched"}, 0, "No projects matched the filters\n")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

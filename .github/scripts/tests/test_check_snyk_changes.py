import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "check-snyk-changes.py"


def write_report(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def run_check(*args):
    output = io.StringIO()
    with patch.object(sys, "argv", [str(SCRIPT), *map(str, args)]):
        with contextlib.redirect_stdout(output):
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit as result:
                return int(result.code), output.getvalue()
    raise AssertionError("The scanner did not return an exit status")


class ChangedFindingsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.root)

    def git(self, *args):
        return subprocess.check_output(["git", *args], text=True).strip()

    def test_dependency_scan_ignores_the_same_path_but_flags_a_new_one(self):
        base_dir = self.root / "baseline"
        base = self.root / "baseline.json"
        current = self.root / "current.json"
        existing = {
            "id": "EXISTING",
            "version": "1",
            "from": ["app@1", "parent@1", "library@1"],
        }
        project = {"projectName": "app", "vulnerabilities": [existing]}
        write_report(base, {**project, "targetFile": str(base_dir / "pnpm-lock.yaml")})
        project["targetFile"] = str(self.root / "pnpm-lock.yaml")
        write_report(current, [project])
        self.assertEqual(run_check("dependencies", base, base_dir, current)[0], 0)

        project["vulnerabilities"].append(
            {**existing, "from": ["app@1", "new-parent@1", "library@1"]}
        )
        write_report(current, [project])
        status, output = run_check("dependencies", base, base_dir, current)
        self.assertEqual(status, 1)
        self.assertIn("new-parent@1", output)

        write_report(current, {"error": "scanner error"})
        with self.assertRaisesRegex(ValueError, "incomplete project result"):
            run_check("dependencies", base, base_dir, current)

    def test_code_scan_matches_traces_on_edited_lines_and_tracks_renames(self):
        self.git("init", "-q")
        self.git("config", "user.name", "CI Fixture")
        self.git("config", "user.email", "ci@example.invalid")
        before = self.root / "before.py"
        before.write_text("one\ntwo\nthree\nfour\nfive\nsix\n")
        (self.root / "unchanged.py").write_text("unchanged\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Base")
        base = self.git("rev-parse", "HEAD")
        self.git("mv", "before.py", "after name.py")
        after = self.root / "after name.py"
        after.write_text("one\ntwo\nchanges\nfour\nfive\nsix\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Changes")

        def location(uri, line):
            return {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": line},
                }
            }

        report = self.root / "code.sarif"
        legacy = {"ruleId": "LEGACY", "locations": [location("after%20name.py", 1)]}
        write_report(report, {"runs": [{"results": [legacy]}]})
        self.assertEqual(run_check("code", report, base)[0], 0)

        new = {
            "ruleId": "NEW",
            "locations": [location("unchanged.py", 1)],
            "codeFlows": [
                {"threadFlows": [{"locations": [{"location": location(after.as_uri(), 3)}]}]}
            ],
        }
        write_report(report, {"runs": [{"results": [legacy, new]}]})
        status, output = run_check("code", report, base)
        self.assertEqual(status, 1)
        self.assertIn("NEW", output)
        self.assertNotIn("LEGACY", output)

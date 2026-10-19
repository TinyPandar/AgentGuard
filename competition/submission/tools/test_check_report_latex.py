"""Regression checks for the report's historical source binding."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_report_latex import check_runtime


class ReportSourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Report binding test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.source = self.repo / "source.py"
        self.source.write_bytes(b"print('baseline')\n")
        self.record = self.repo / "record.json"
        self.write_record(hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.binding = self.commit_binding()

    def git(self, *arguments):
        return subprocess.check_output(
            ["git", "-c", f"core.hooksPath={self.repo / 'no-hooks'}", *arguments],
            cwd=self.repo,
            stderr=subprocess.PIPE,
        )

    def write_record(self, source_hash):
        self.record.write_bytes(
            json.dumps({"candidate_source_hashes": {"source.py": source_hash}}).encode()
        )

    def commit_binding(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "Synthetic report snapshot")
        return {
            "schema": "sujie-report-source-binding-v1",
            "source_commit": self.git("rev-parse", "HEAD").decode().strip(),
            "validation_record": "record.json",
            "validation_record_sha256": hashlib.sha256(
                self.record.read_bytes()
            ).hexdigest(),
        }

    def test_snapshot_matches_and_current_tree_is_reported(self):
        result = check_runtime(self.repo, self.binding)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["source_files_checked"], 1)
        self.assertTrue(result["current_source_matches_report"])

    def test_later_code_is_distinct_from_historical_evidence(self):
        self.source.write_bytes(b"print('new version')\n")
        self.git("add", "source.py")
        self.git("commit", "-qm", "Later code")
        result = check_runtime(self.repo, self.binding)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["source_mismatches"], [])
        self.assertEqual(result["current_source_mismatches"], ["source.py"])
        self.assertFalse(result["current_source_matches_report"])
        self.assertIn("cited_snapshot_only", result["runtime_acceptance_scope"])

    def test_strict_mode_rejects_current_tree_drift(self):
        self.source.write_bytes(b"print('changed')\n")
        result = check_runtime(self.repo, self.binding, require_current=True)
        self.assertTrue(result["errors"])
        self.assertTrue(result["current_source_required"])

    def test_record_digest_cannot_be_silently_replaced(self):
        with self.assertRaisesRegex(ValueError, "record digest mismatch"):
            check_runtime(
                self.repo, self.binding | {"validation_record_sha256": "0" * 64}
            )

    def test_wrong_frozen_source_hash_still_fails(self):
        self.write_record("0" * 64)
        binding = self.commit_binding()
        result = check_runtime(self.repo, binding)
        self.assertEqual(result["source_mismatches"], ["source.py"])
        self.assertTrue(result["errors"])

    def test_missing_source_or_commit_fails(self):
        self.source.unlink()
        binding = self.commit_binding()
        with self.assertRaisesRegex(ValueError, "Git blob unavailable"):
            check_runtime(self.repo, binding)
        with self.assertRaisesRegex(ValueError, "Git blob unavailable"):
            check_runtime(self.repo, self.binding | {"source_commit": "0" * 40})

    def test_unsafe_record_path_is_rejected(self):
        for path in ("../record.json", "/record.json", "record.json\nHEAD:source.py"):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ValueError, "Invalid report source binding"),
            ):
                check_runtime(self.repo, self.binding | {"validation_record": path})


if __name__ == "__main__":
    unittest.main()

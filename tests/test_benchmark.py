import unittest
from pathlib import Path

from agentguard.benchmark import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_full_guard_reduces_execution_asr_without_breaking_benign_tasks(
        self,
    ) -> None:
        dataset = Path(__file__).resolve().parent.parent / "benchmark" / "cases.jsonl"
        report = run_benchmark(dataset)
        unsafe = report["metrics"]["unsafe"]
        rule = report["metrics"]["rule_guard"]
        full = report["metrics"]["full"]

        self.assertEqual(unsafe["execution_asr"], 1.0)
        self.assertGreater(rule["execution_asr"], full["execution_asr"])
        self.assertEqual(full["execution_asr"], 0.0)
        self.assertEqual(full["sensitive_leakage_rate"], 0.0)
        self.assertEqual(full["normal_task_success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

import unittest

from experiments.compare_schedulers import SCENARIOS, measure, schedule


class SchedulerBenchmarkTest(unittest.TestCase):
    def test_both_strategies_complete_identical_work(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                legacy = {task.id for task in schedule(scenario, "legacy_dfs")}
                proof = {task.id for task in schedule(scenario, "proof_first")}
                self.assertEqual(legacy, proof)

    def test_contained_feature_is_neutral_control(self):
        scenario = SCENARIOS[0]
        legacy = measure(scenario, "legacy_dfs")
        proof = measure(scenario, "proof_first")
        self.assertEqual(legacy["time_to_proof"], proof["time_to_proof"])
        self.assertEqual(legacy["total_with_rework"], proof["total_with_rework"])

    def test_cross_capability_proof_arrives_earlier(self):
        scenario = SCENARIOS[1]
        legacy = measure(scenario, "legacy_dfs")
        proof = measure(scenario, "proof_first")
        self.assertLess(proof["time_to_proof"], legacy["time_to_proof"])
        self.assertEqual(legacy["planned_work"], proof["planned_work"])

    def test_early_failure_reduces_rework(self):
        scenario = SCENARIOS[2]
        legacy = measure(scenario, "legacy_dfs")
        proof = measure(scenario, "proof_first")
        self.assertLess(proof["rework_if_proof_fails"], legacy["rework_if_proof_fails"])
        self.assertLess(proof["total_with_rework"], legacy["total_with_rework"])


if __name__ == "__main__":
    unittest.main()

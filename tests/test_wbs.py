import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


WBS = Path(__file__).resolve().parents[1] / "wbs.py"


def leaf(node_id, *, dependencies=None, status="pending", verify=None):
    verify = ["true"] if verify is None else verify
    return {
        "id": node_id,
        "type": "work_package",
        "title": node_id,
        "objective": f"Deliver {node_id}",
        "status": status,
        "acceptance_criteria": [f"{node_id} works"],
        "verify": verify,
        "dependencies": dependencies or [],
        "children": [],
    }


def tree_with(children, *, proof_slice=None, meta_verify=None):
    data = {
        "meta": {"project": "test", "verify": meta_verify or []},
        "tree": {
            "id": "ROOT",
            "type": "product",
            "title": "Test product",
            "objective": "Exercise the WBS manager",
            "status": "pending",
            "acceptance_criteria": ["All children complete"],
            "dependencies": [],
            "children": children,
        },
    }
    if proof_slice is not None:
        data["proof_slice"] = proof_slice
    return data


def proof(nodes, *, status="pending", verify=None):
    return {
        "id": "PROOF-FIRST-JOURNEY",
        "objective": "Complete the first journey end to end",
        "hypothesis": "The system boundaries compose",
        "nodes": nodes,
        "acceptance_criteria": ["The first journey works"],
        "verify": verify or ["true"],
        "status": status,
    }


class WbsCliTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.tree_path = Path(self.temp_dir.name) / "tree.yaml"

    def write_tree(self, data):
        self.tree_path.write_text(yaml.safe_dump(data, sort_keys=False))

    def read_tree(self):
        return yaml.safe_load(self.tree_path.read_text())

    def run_wbs(self, *args):
        return subprocess.run(
            [sys.executable, str(WBS), "--tree", str(self.tree_path), *args],
            cwd=self.temp_dir.name,
            capture_output=True,
            text=True,
        )

    def assert_success_json(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_init_scaffolds_outcome_ledger_before_technical_mapping(self):
        prd_path = Path(self.temp_dir.name) / "prd.md"
        prd_path.write_text("# Product\n")

        self.assert_success_json(self.run_wbs("init", str(prd_path)))

        context = (Path(self.temp_dir.name) / "context.md").read_text()
        self.assertIn("## Outcome Requirements", context)
        self.assertIn("## Delivery Branches", context)
        self.assertEqual(self.read_tree()["tree"]["source_requirements"], [])
        self.assertEqual(
            self.read_tree()["meta"]["execution_strategy"], "proof_slice_first"
        )
        self.assertTrue((Path(self.temp_dir.name) / "node-template.yaml").exists())

    def test_legacy_tree_keeps_depth_first_selection(self):
        self.write_tree(tree_with([leaf("FIRST"), leaf("SECOND")]))

        output = self.assert_success_json(self.run_wbs("next"))

        self.assertEqual(output["id"], "FIRST")
        self.assertNotIn("proof_slice", output)

    def test_missing_strategy_defaults_to_proof_slice_first(self):
        self.write_tree(
            tree_with(
                [leaf("OUTSIDE"), leaf("PROOF-NODE")],
                proof_slice=proof(["PROOF-NODE"]),
            )
        )

        next_output = self.assert_success_json(self.run_wbs("next"))
        status_output = self.assert_success_json(self.run_wbs("status"))

        self.assertEqual(next_output["id"], "PROOF-NODE")
        self.assertEqual(status_output["execution_strategy"], "proof_slice_first")

    def test_legacy_bottom_up_strategy_bypasses_proof_gate(self):
        data = tree_with(
            [leaf("OUTSIDE"), leaf("PROOF-NODE")],
            proof_slice=proof(["PROOF-NODE"]),
        )
        data["meta"]["execution_strategy"] = "legacy_bottom_up"
        self.write_tree(data)

        next_output = self.assert_success_json(self.run_wbs("next"))
        done_output = self.assert_success_json(self.run_wbs("done", "OUTSIDE"))
        status_output = self.assert_success_json(self.run_wbs("status"))

        self.assertEqual(next_output["id"], "OUTSIDE")
        self.assertEqual(done_output["marked_complete"], "OUTSIDE")
        self.assertFalse(status_output["proof_slice"]["enforced"])

    def test_strategy_command_reads_and_persists_selection(self):
        self.write_tree(tree_with([leaf("FIRST")]))

        initial = self.assert_success_json(self.run_wbs("strategy"))
        changed = self.assert_success_json(
            self.run_wbs("strategy", "legacy_bottom_up")
        )
        current = self.assert_success_json(self.run_wbs("strategy"))

        self.assertEqual(initial["execution_strategy"], "proof_slice_first")
        self.assertEqual(initial["source"], "default")
        self.assertEqual(changed["execution_strategy"], "legacy_bottom_up")
        self.assertEqual(current["source"], "meta")
        self.assertEqual(
            self.read_tree()["meta"]["execution_strategy"], "legacy_bottom_up"
        )

    def test_invalid_execution_strategy_fails_validation(self):
        data = tree_with([leaf("FIRST")])
        data["meta"]["execution_strategy"] = "fastest"
        self.write_tree(data)

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("execution_strategy", result.stdout)

    def test_completed_legacy_tree_reports_no_executable_leaves(self):
        self.write_tree(tree_with([leaf("ONLY", status="complete")]))

        output = self.assert_success_json(self.run_wbs("status"))

        self.assertIsNone(output["next"])
        self.assertEqual(output["scheduler_status"], "no_executable_leaves")

    def test_invalid_tree_prevents_next_and_status(self):
        invalid = tree_with([leaf("FIRST")])
        invalid["tree"]["children"][0]["acceptance_criteria"] = []
        self.write_tree(invalid)

        for command in ("next", "status"):
            with self.subTest(command=command):
                result = self.run_wbs(command)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("tree validation failed", result.stderr)
                self.assertIn("acceptance_criteria", result.stderr)

    def test_invalid_yaml_reports_a_bounded_cli_error(self):
        self.tree_path.write_text("tree: [unterminated\n")

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contains invalid YAML", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_source_requirements_must_be_string_ids_when_present(self):
        invalid = tree_with([leaf("FIRST")])
        invalid["tree"]["children"][0]["source_requirements"] = ["REQ-001", 2]
        self.write_tree(invalid)

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_requirements", result.stdout)

    def test_leaf_requires_node_or_project_verification(self):
        data = tree_with([leaf("FIRST", verify=[])])
        self.write_tree(data)

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("leaf has no verification commands", result.stdout)

    def test_project_verification_can_supply_leaf_gate(self):
        data = tree_with([leaf("FIRST", verify=[])], meta_verify=["true"])
        self.write_tree(data)

        result = self.run_wbs("validate")

        self.assert_success_json(result)

    def test_verification_fields_must_be_lists_of_non_empty_strings(self):
        cases = [
            ("node", tree_with([leaf("FIRST", verify="true")]), "FIRST: 'verify'"),
            ("meta", tree_with([leaf("FIRST")], meta_verify={"cmd": "true"}), "meta.verify"),
            (
                "proof",
                tree_with(
                    [leaf("FIRST")],
                    proof_slice=proof(["FIRST"], verify=[1]),
                ),
                "proof_slice.verify",
            ),
        ]

        for name, data, expected in cases:
            with self.subTest(name=name):
                self.write_tree(data)
                result = self.run_wbs("validate")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)

    def test_acceptance_criteria_must_be_non_empty_strings(self):
        data = tree_with([leaf("FIRST")])
        data["tree"]["children"][0]["acceptance_criteria"] = [""]
        self.write_tree(data)

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("acceptance_criteria", result.stdout)

    def test_next_preserves_requirement_traceability(self):
        first = leaf("FIRST")
        first["source_requirements"] = ["REQ-001"]
        self.write_tree(tree_with([first]))

        output = self.assert_success_json(self.run_wbs("next"))

        self.assertEqual(output["source_requirements"], ["REQ-001"])

    def test_start_rejects_unmet_dependency(self):
        self.write_tree(
            tree_with(
                [
                    leaf("BASE"),
                    leaf("DEPENDENT", dependencies=[{"id": "BASE", "type": "data"}]),
                ]
            )
        )

        result = self.run_wbs("start", "DEPENDENT")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete dependencies: BASE", result.stderr)
        self.assertEqual(self.read_tree()["tree"]["children"][1]["status"], "pending")

    def test_start_rejects_non_leaf(self):
        parent = {
            "id": "PARENT",
            "type": "feature",
            "title": "Parent",
            "objective": "Group work",
            "status": "pending",
            "acceptance_criteria": ["Child completes"],
            "dependencies": [],
            "children": [leaf("CHILD")],
        }
        self.write_tree(tree_with([parent]))

        result = self.run_wbs("start", "PARENT")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not an executable leaf", result.stderr)

    def test_done_rejects_unmet_dependency(self):
        self.write_tree(
            tree_with(
                [
                    leaf("BASE"),
                    leaf("DEPENDENT", dependencies=[{"id": "BASE", "type": "data"}]),
                ]
            )
        )

        result = self.run_wbs("done", "DEPENDENT")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete dependencies: BASE", result.stderr)
        self.assertEqual(self.read_tree()["tree"]["children"][1]["status"], "pending")

    def test_verification_failure_does_not_mutate_tree(self):
        self.write_tree(tree_with([leaf("FIRST", verify=["false"])]))
        before = self.tree_path.read_text()

        result = self.run_wbs("done", "FIRST")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree_path.read_text(), before)

    def test_project_verification_failure_does_not_mutate_tree(self):
        self.write_tree(tree_with([leaf("FIRST")], meta_verify=["false"]))
        before = self.tree_path.read_text()

        result = self.run_wbs("done", "FIRST")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree_path.read_text(), before)

    def test_proof_slice_selects_across_tree_before_non_proof_work(self):
        auth = {
            "id": "CAP-AUTH",
            "type": "capability",
            "title": "Auth",
            "objective": "Authenticate users",
            "status": "pending",
            "acceptance_criteria": ["Auth works"],
            "dependencies": [],
            "children": [leaf("AUTH-PROOF", status="complete"), leaf("AUTH-LATER")],
        }
        workspace = {
            "id": "CAP-WORKSPACE",
            "type": "capability",
            "title": "Workspace",
            "objective": "Create workspaces",
            "status": "pending",
            "acceptance_criteria": ["Workspace works"],
            "dependencies": [],
            "children": [
                leaf(
                    "WORKSPACE-PROOF",
                    dependencies=[{"id": "AUTH-PROOF", "type": "data"}],
                )
            ],
        }
        self.write_tree(
            tree_with(
                [auth, workspace],
                proof_slice=proof(["AUTH-PROOF", "WORKSPACE-PROOF"]),
            )
        )

        output = self.assert_success_json(self.run_wbs("next"))

        self.assertEqual(output["id"], "WORKSPACE-PROOF")
        self.assertEqual(output["proof_slice"]["id"], "PROOF-FIRST-JOURNEY")

    def test_non_proof_start_and_done_are_blocked_until_approval(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE"), leaf("LATER")],
                proof_slice=proof(["PROOF-NODE"]),
            )
        )

        for command in ("start", "done"):
            with self.subTest(command=command):
                result = self.run_wbs(command, "LATER")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("outside active proof slice", result.stderr)

    def test_proof_dependency_closure_is_validated(self):
        self.write_tree(
            tree_with(
                [
                    leaf("BASE"),
                    leaf("PROOF-NODE", dependencies=[{"id": "BASE", "type": "data"}]),
                ],
                proof_slice=proof(["PROOF-NODE"]),
            )
        )

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn(
            "proof_slice: unresolved dependency 'BASE' for 'PROOF-NODE' is not in the proof slice",
            output["errors"],
        )

    def test_blocked_proof_reports_why_no_member_is_executable(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE", status="blocked")],
                proof_slice=proof(["PROOF-NODE"]),
            )
        )

        output = self.assert_success_json(self.run_wbs("next"))

        self.assertEqual(output["status"], "proof_slice_blocked")
        self.assertEqual(output["blocked_nodes"]["PROOF-NODE"]["status"], "blocked")

    def test_verified_proof_requires_complete_members(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE")],
                proof_slice=proof(["PROOF-NODE"], status="verified"),
            )
        )

        result = self.run_wbs("validate")

        self.assertNotEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn(
            "proof_slice: status 'verified' requires complete member nodes: PROOF-NODE",
            output["errors"],
        )

    def test_final_proof_verification_failure_is_atomic(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE")],
                proof_slice=proof(["PROOF-NODE"], verify=["false"]),
            )
        )
        before = self.tree_path.read_text()

        result = self.run_wbs("done", "PROOF-NODE")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("proof slice verify failed", result.stderr)
        self.assertEqual(self.tree_path.read_text(), before)

    def test_passing_proof_waits_for_approval_then_unlocks_tree(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE"), leaf("LATER")],
                proof_slice=proof(["PROOF-NODE"]),
            )
        )

        done = self.assert_success_json(self.run_wbs("done", "PROOF-NODE"))
        self.assertEqual(done["proof_slice_status"], "verified")
        self.assertEqual(done["status"], "awaiting_proof_approval")

        waiting = self.assert_success_json(self.run_wbs("next"))
        self.assertEqual(waiting["status"], "awaiting_proof_approval")
        self.assertIsNone(waiting["next"])

        approved = self.assert_success_json(self.run_wbs("approve-proof"))
        self.assertEqual(approved["proof_slice_status"], "approved")
        self.assertIn("approved_at", approved)

        next_node = self.assert_success_json(self.run_wbs("next"))
        self.assertEqual(next_node["id"], "LATER")

    def test_approve_proof_rechecks_verification_without_mutation_on_failure(self):
        self.write_tree(
            tree_with(
                [leaf("PROOF-NODE", status="complete")],
                proof_slice=proof(["PROOF-NODE"], status="verified", verify=["false"]),
            )
        )
        before = self.tree_path.read_text()

        result = self.run_wbs("approve-proof")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("proof slice verify failed", result.stderr)
        self.assertEqual(self.tree_path.read_text(), before)

    def test_normal_completion_still_propagates_and_is_idempotent(self):
        self.write_tree(tree_with([leaf("ONLY")]))

        first = self.assert_success_json(self.run_wbs("done", "ONLY"))
        self.assertEqual(first["propagated_complete"], ["ROOT"])

        second = self.assert_success_json(self.run_wbs("done", "ONLY"))
        self.assertEqual(second, {"already_complete": "ONLY"})


if __name__ == "__main__":
    unittest.main()

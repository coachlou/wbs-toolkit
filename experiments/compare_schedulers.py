#!/usr/bin/env python3
"""Deterministic A/B benchmark for legacy DFS and Proof-Slice-first ordering."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    cost: int
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    name: str
    tasks: tuple[Task, ...]
    proof: tuple[str, ...]
    invalidated_on_failed_proof: tuple[str, ...] = ()


SCENARIOS = (
    Scenario(
        name="contained_feature_control",
        tasks=(
            Task("DATA", 3),
            Task("API", 3, ("DATA",)),
            Task("UI", 3, ("API",)),
            Task("REPORTING", 4),
            Task("ADMIN", 4),
        ),
        proof=("DATA", "API", "UI"),
    ),
    Scenario(
        name="cross_capability_no_failure",
        tasks=(
            Task("AUTH-HARDEN", 5),
            Task("AUTH-PROOF", 2),
            Task("AUTH-LATER", 4, ("AUTH-PROOF",)),
            Task("DATA-PROOF", 3, ("AUTH-PROOF",)),
            Task("DATA-LATER", 5, ("DATA-PROOF",)),
            Task("UI-PROOF", 3, ("DATA-PROOF",)),
            Task("UI-LATER", 5, ("UI-PROOF",)),
        ),
        proof=("AUTH-PROOF", "DATA-PROOF", "UI-PROOF"),
    ),
    Scenario(
        name="cross_capability_failed_boundary",
        tasks=(
            Task("AUTH-HARDEN", 5),
            Task("AUTH-PROOF", 2),
            Task("AUTH-LATER", 4, ("AUTH-PROOF",)),
            Task("DATA-PROOF", 3, ("AUTH-PROOF",)),
            Task("DATA-LATER", 5, ("DATA-PROOF",)),
            Task("UI-PROOF", 3, ("DATA-PROOF",)),
            Task("UI-LATER", 5, ("UI-PROOF",)),
        ),
        proof=("AUTH-PROOF", "DATA-PROOF", "UI-PROOF"),
        invalidated_on_failed_proof=(
            "AUTH-HARDEN",
            "AUTH-LATER",
            "DATA-LATER",
            "UI-LATER",
        ),
    ),
)


def executable(task: Task, completed: set[str]) -> bool:
    return all(dependency in completed for dependency in task.dependencies)


def schedule(scenario: Scenario, strategy: str) -> list[Task]:
    remaining = list(scenario.tasks)
    completed: set[str] = set()
    ordered: list[Task] = []
    proof_set = set(scenario.proof)

    while remaining:
        candidates = [task for task in remaining if executable(task, completed)]
        if not candidates:
            raise ValueError(f"{scenario.name}: dependency deadlock")
        if strategy == "proof_first" and not proof_set.issubset(completed):
            proof_candidates = [task for task in candidates if task.id in proof_set]
            if not proof_candidates:
                raise ValueError(f"{scenario.name}: proof is not dependency closed")
            chosen = proof_candidates[0]
        else:
            chosen = candidates[0]
        remaining.remove(chosen)
        completed.add(chosen.id)
        ordered.append(chosen)
    return ordered


def measure(scenario: Scenario, strategy: str) -> dict:
    ordered = schedule(scenario, strategy)
    proof_set = set(scenario.proof)
    elapsed = 0
    completed_at_proof: set[str] = set()
    time_to_proof = None
    for task in ordered:
        elapsed += task.cost
        completed_at_proof.add(task.id)
        if proof_set.issubset(completed_at_proof):
            time_to_proof = elapsed
            break

    wasted = sum(
        task.cost
        for task in scenario.tasks
        if task.id in completed_at_proof
        and task.id in scenario.invalidated_on_failed_proof
    )
    total = sum(task.cost for task in scenario.tasks)
    return {
        "strategy": strategy,
        "order": [task.id for task in ordered],
        "time_to_proof": time_to_proof,
        "planned_work": total,
        "rework_if_proof_fails": wasted,
        "total_with_rework": total + wasted,
    }


def run() -> dict:
    results = []
    for scenario in SCENARIOS:
        baseline = measure(scenario, "legacy_dfs")
        proof_first = measure(scenario, "proof_first")
        results.append(
            {
                "scenario": scenario.name,
                "legacy_dfs": baseline,
                "proof_first": proof_first,
                "delta": {
                    "time_to_proof": proof_first["time_to_proof"]
                    - baseline["time_to_proof"],
                    "total_with_rework": proof_first["total_with_rework"]
                    - baseline["total_with_rework"],
                },
            }
        )
    return {"cost_unit": "abstract serial work unit", "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(), indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

# /// script
# dependencies = ["pyyaml"]
# ///
"""
wbs.py — Recursive Work Breakdown Structure manager for AI-driven development.

The AI agent (Claude Code / Codex) IS the executor. This tool manages tree state.

Commands:
  next                   Next executable leaf (JSON) — the main loop driver
  show <id>             Node + parent chain (JSON) — load into agent context
  done <id>             Mark complete, propagate status upward
  start <id>            Mark in_progress
  block <id>            Mark blocked (--reason optional)
  decompose <id>        Mark decomposed; edit tree.yaml to add children, then validate
  strategy [name]       Show or persist the execution strategy
  approve-proof         Approve a verified proof slice and unlock ordinary traversal
  status                Progress dashboard
  validate              Validate tree.yaml schema and integrity
  init <prd.md>         Scaffold .wbs/tree.yaml from PRD (PRD skill populates the real content)

Options:
  --tree PATH           Path to tree.yaml [default: .wbs/tree.yaml]

Successful commands emit JSON to stdout. Validation reports always use stdout;
operational errors use stderr. Failures exit non-zero.
Run with: python wbs.py <command> or uv run wbs.py <command>
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_TREE = Path(".wbs/tree.yaml")
TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_NODE_TEMPLATE = TOOL_ROOT / ".wbs/node-template.yaml"

VALID_TYPES = {
    "product",
    "capability",
    "feature",
    "module",
    "work_package",
    "task",
    "step",
}
VALID_STATUSES = {
    "pending",
    "ready",
    "in_progress",
    "complete",
    "blocked",
    "decomposed",
}
VALID_DEP_TYPES = {"data", "sequence", "runtime"}
VALID_PROOF_STATUSES = {"pending", "verified", "approved"}
DEFAULT_EXECUTION_STRATEGY = "proof_slice_first"
VALID_EXECUTION_STRATEGIES = {"proof_slice_first", "legacy_bottom_up"}
REQUIRED_FIELDS = ("id", "type", "title", "objective", "status")
REQUIRED_PROOF_FIELDS = (
    "id",
    "objective",
    "hypothesis",
    "nodes",
    "acceptance_criteria",
    "verify",
    "status",
)


# ── Tree I/O ──────────────────────────────────────────────────────────────────


def load_tree(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"Error: {path} not found. Run 'wbs.py init <prd.md>' first.")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        sys.exit(f"Error: {path} contains invalid YAML: {exc}")
    if not isinstance(data, dict) or "tree" not in data:
        sys.exit(f"Error: {path} must contain a 'tree' key at the top level.")
    return data


def save_tree(data: dict, path: Path) -> None:
    """Atomically replace the tree so an interrupted write cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as f:
            temp_path = Path(f.name)
            yaml.dump(
                data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp_path, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


# ── Node index ────────────────────────────────────────────────────────────────


def build_index(
    node: dict, index: Optional[dict] = None, parent_chain: Optional[list] = None
) -> dict:
    """Flat {id: (node_dict, parent_chain)} for O(1) lookup across the whole tree."""
    if index is None:
        index = {}
    if parent_chain is None:
        parent_chain = []
    index[node["id"]] = (node, parent_chain)
    for child in node.get("children") or []:
        build_index(child, index, parent_chain + [node])
    return index


def find_node(tree_data: dict, node_id: str) -> tuple:
    """Returns (node, parent_chain) or (None, []) if not found."""
    index = build_index(tree_data["tree"])
    return index.get(node_id, (None, []))


# ── Leaf detection ────────────────────────────────────────────────────────────


def is_leaf(node: dict) -> bool:
    return not node.get("children")


def is_executable(node: dict, index: dict) -> bool:
    """Leaf with all dependencies complete and status pending or ready."""
    if not is_leaf(node):
        return False
    if node.get("status") not in ("pending", "ready"):
        return False
    for dep in node.get("dependencies") or []:
        dep_id = dep if isinstance(dep, str) else dep.get("id", "")
        dep_entry = index.get(dep_id)
        if dep_entry is None or dep_entry[0].get("status") != "complete":
            return False
    return True


def find_next_leaf(node: dict, index: dict) -> Optional[dict]:
    """Depth-first search returning the first executable leaf."""
    if is_executable(node, index):
        return node
    for child in node.get("children") or []:
        result = find_next_leaf(child, index)
        if result:
            return result
    return None


def dependency_id(dep) -> str:
    return dep if isinstance(dep, str) else dep.get("id", "")


def incomplete_dependencies(node: dict, index: dict) -> list[str]:
    incomplete = []
    for dep in node.get("dependencies") or []:
        dep_id = dependency_id(dep)
        dep_entry = index.get(dep_id)
        if dep_entry is None or dep_entry[0].get("status") != "complete":
            incomplete.append(dep_id)
    return incomplete


# ── Validation ────────────────────────────────────────────────────────────────


def validate_tree_data(tree_data: dict) -> tuple[list[str], dict]:
    """Return validation errors and a safe node index without mutating the tree."""
    errors = []
    index = {}
    seen = set()

    if "meta" not in tree_data:
        errors.append("Missing top-level 'meta' section.")
        meta = {}
    elif not isinstance(tree_data["meta"], dict):
        errors.append("Top-level 'meta' must be a mapping.")
        meta = {}
    else:
        meta = tree_data["meta"]

    def validate_string_list(value, label, *, required=False) -> bool:
        if not isinstance(value, list):
            errors.append(f"{label}: must be a list of non-empty strings")
            return False
        if any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{label}: every item must be a non-empty string")
            return False
        if required and not value:
            errors.append(f"{label}: must contain at least one item")
            return False
        return True

    meta_verify = meta.get("verify", [])
    meta_verify_valid = validate_string_list(meta_verify, "meta.verify")
    has_meta_verify = meta_verify_valid and bool(meta_verify)

    configured_strategy = meta.get("execution_strategy")
    if (
        configured_strategy is not None
        and configured_strategy not in VALID_EXECUTION_STRATEGIES
    ):
        errors.append(
            "meta.execution_strategy: invalid value "
            f"'{configured_strategy}' — must be one of {sorted(VALID_EXECUTION_STRATEGIES)}"
        )

    root = tree_data.get("tree")
    if not isinstance(root, dict):
        return errors + ["Top-level 'tree' must be a node mapping."], index

    def visit(node, parent_chain, location):
        if not isinstance(node, dict):
            errors.append(f"{location}: node must be a mapping")
            return

        node_id = node.get("id")
        label = node_id if isinstance(node_id, str) and node_id else location

        for field in REQUIRED_FIELDS:
            if field not in node:
                errors.append(f"{label}: missing required field '{field}'")

        if isinstance(node_id, str) and node_id:
            if node_id in seen:
                errors.append(f"Duplicate node ID: '{node_id}'")
            else:
                seen.add(node_id)
                index[node_id] = (node, parent_chain)
        elif "id" in node:
            errors.append(f"{location}: field 'id' must be a non-empty string")

        if node.get("type") not in VALID_TYPES:
            errors.append(
                f"{label}: invalid type '{node.get('type')}' — must be one of {sorted(VALID_TYPES)}"
            )
        if node.get("status") not in VALID_STATUSES:
            errors.append(
                f"{label}: invalid status '{node.get('status')}' — must be one of {sorted(VALID_STATUSES)}"
            )

        source_requirements = node.get("source_requirements")
        if source_requirements is not None and (
            not isinstance(source_requirements, list)
            or any(
                not isinstance(requirement_id, str) or not requirement_id
                for requirement_id in source_requirements
            )
        ):
            errors.append(
                f"{label}: 'source_requirements' must be a list of non-empty strings"
            )

        children = node.get("children") or []
        if not isinstance(children, list):
            errors.append(f"{label}: 'children' must be a list")
            children = []

        if not children and node.get("status") != "decomposed":
            validate_string_list(
                node.get("acceptance_criteria"),
                f"{label}: 'acceptance_criteria'",
                required=True,
            )

            node_verify = node.get("verify", [])
            node_verify_valid = validate_string_list(
                node_verify, f"{label}: 'verify'"
            )
            if node_verify_valid and not node_verify and not has_meta_verify:
                errors.append(
                    f"{label}: leaf has no verification commands — add node 'verify' or meta.verify"
                )
        elif "acceptance_criteria" in node:
            validate_string_list(
                node.get("acceptance_criteria"),
                f"{label}: 'acceptance_criteria'",
            )

        if children and "verify" in node:
            validate_string_list(node.get("verify"), f"{label}: 'verify'")

        dependencies = node.get("dependencies") or []
        if not isinstance(dependencies, list):
            errors.append(f"{label}: 'dependencies' must be a list")

        for position, child in enumerate(children):
            visit(child, parent_chain + [node], f"{location}.children[{position}]")

    visit(root, [], "tree")

    for node_id, (node, _) in index.items():
        dependencies = node.get("dependencies") or []
        if not isinstance(dependencies, list):
            continue
        for dep in dependencies:
            if isinstance(dep, str):
                dep_id = dep
                dep_type = None
            elif isinstance(dep, dict):
                dep_id = dep.get("id", "")
                dep_type = dep.get("type")
            else:
                errors.append(f"{node_id}: dependency must be a string or mapping")
                continue
            if dep_id not in index:
                errors.append(f"{node_id}: dependency '{dep_id}' not found in tree")
            if dep_type and dep_type not in VALID_DEP_TYPES:
                errors.append(
                    f"{node_id}: dependency type '{dep_type}' invalid — must be one of {sorted(VALID_DEP_TYPES)}"
                )

    graph = {}
    for node_id, (node, _) in index.items():
        edges = [
            child.get("id")
            for child in (node.get("children") or [])
            if isinstance(child, dict) and child.get("id") in index
        ]
        dependencies = node.get("dependencies") or []
        if isinstance(dependencies, list):
            edges.extend(
                dependency_id(dep)
                for dep in dependencies
                if isinstance(dep, (str, dict)) and dependency_id(dep) in index
            )
        graph[node_id] = edges

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)

    def find_cycle(node_id, path):
        color[node_id] = GRAY
        path.append(node_id)
        for neighbor in graph[node_id]:
            if color[neighbor] == GRAY:
                cycle = path[path.index(neighbor) :] + [neighbor]
                errors.append(f"Dependency cycle: {' -> '.join(cycle)}")
                path.pop()
                color[node_id] = BLACK
                return True
            if color[neighbor] == WHITE and find_cycle(neighbor, path):
                path.pop()
                color[node_id] = BLACK
                return True
        path.pop()
        color[node_id] = BLACK
        return False

    for node_id in graph:
        if color[node_id] == WHITE and find_cycle(node_id, []):
            break

    proof = tree_data.get("proof_slice")
    if proof is not None:
        if not isinstance(proof, dict):
            errors.append("proof_slice: must be a mapping")
        else:
            for field in REQUIRED_PROOF_FIELDS:
                if field not in proof:
                    errors.append(f"proof_slice: missing required field '{field}'")

            proof_status = proof.get("status")
            if proof_status not in VALID_PROOF_STATUSES:
                errors.append(
                    f"proof_slice: invalid status '{proof_status}' — must be one of {sorted(VALID_PROOF_STATUSES)}"
                )

            proof_nodes = proof.get("nodes")
            if not isinstance(proof_nodes, list) or not proof_nodes:
                errors.append("proof_slice: 'nodes' must be a non-empty list")
                proof_nodes = []
            elif any(not isinstance(node_id, str) or not node_id for node_id in proof_nodes):
                errors.append("proof_slice: every node ID must be a non-empty string")
                proof_nodes = [
                    node_id
                    for node_id in proof_nodes
                    if isinstance(node_id, str) and node_id
                ]

            if len(proof_nodes) != len(set(proof_nodes)):
                errors.append("proof_slice: 'nodes' contains duplicate IDs")

            validate_string_list(
                proof.get("acceptance_criteria"),
                "proof_slice.acceptance_criteria",
                required=True,
            )
            validate_string_list(
                proof.get("verify"), "proof_slice.verify", required=True
            )

            proof_set = set(proof_nodes)
            for proof_node_id in proof_nodes:
                entry = index.get(proof_node_id)
                if entry is None:
                    errors.append(f"proof_slice: node '{proof_node_id}' not found in tree")
                    continue
                proof_node = entry[0]
                if not is_leaf(proof_node):
                    errors.append(f"proof_slice: node '{proof_node_id}' must be a leaf")
                for dep in proof_node.get("dependencies") or []:
                    dep_id = dependency_id(dep)
                    dep_entry = index.get(dep_id)
                    if (
                        dep_entry is not None
                        and dep_entry[0].get("status") != "complete"
                        and dep_id not in proof_set
                    ):
                        errors.append(
                            f"proof_slice: unresolved dependency '{dep_id}' for '{proof_node_id}' is not in the proof slice"
                        )

            if proof_status in ("verified", "approved"):
                incomplete = [
                    node_id
                    for node_id in proof_nodes
                    if node_id in index and index[node_id][0].get("status") != "complete"
                ]
                if incomplete:
                    errors.append(
                        "proof_slice: status "
                        f"'{proof_status}' requires complete member nodes: {', '.join(incomplete)}"
                    )

    return errors, index


def load_valid_tree(path: Path) -> dict:
    tree_data = load_tree(path)
    errors, _ = validate_tree_data(tree_data)
    if errors:
        sys.exit("Error: tree validation failed:\n- " + "\n- ".join(errors))
    return tree_data


def execution_strategy(tree_data: dict) -> str:
    meta = tree_data.get("meta")
    if not isinstance(meta, dict):
        return DEFAULT_EXECUTION_STRATEGY
    return meta.get("execution_strategy", DEFAULT_EXECUTION_STRATEGY)


def active_proof_slice(tree_data: dict) -> Optional[dict]:
    if execution_strategy(tree_data) != "proof_slice_first":
        return None
    proof = tree_data.get("proof_slice")
    if proof and proof.get("status") != "approved":
        return proof
    return None


def assert_proof_allows(tree_data: dict, node_id: str) -> None:
    proof = active_proof_slice(tree_data)
    if proof is None:
        return
    if proof.get("status") == "verified":
        sys.exit(
            f"Error: proof slice '{proof['id']}' is verified and awaiting approval; no additional work may start or complete."
        )
    if node_id not in proof.get("nodes", []):
        sys.exit(
            f"Error: node '{node_id}' is outside active proof slice '{proof['id']}'."
        )


def proof_selection(tree_data: dict, index: dict) -> tuple[Optional[dict], Optional[dict]]:
    proof = active_proof_slice(tree_data)
    if proof is None:
        return None, None
    if proof.get("status") == "verified":
        return None, {
            "status": "awaiting_proof_approval",
            "proof_slice": proof["id"],
            "next": None,
            "message": "The proof slice is verified. Run 'wbs.py approve-proof' after human review.",
        }

    for node_id in proof["nodes"]:
        node = index[node_id][0]
        if is_executable(node, index):
            return node, None

    blocked = {}
    for node_id in proof["nodes"]:
        node = index[node_id][0]
        if node.get("status") == "complete":
            continue
        blocked[node_id] = {
            "status": node.get("status"),
            "incomplete_dependencies": incomplete_dependencies(node, index),
        }
    return None, {
        "status": "proof_slice_blocked",
        "proof_slice": proof["id"],
        "next": None,
        "blocked_nodes": blocked,
        "message": "No incomplete proof-slice member is currently executable.",
    }


# ── Verification ──────────────────────────────────────────────────────────────


def run_verify(node: dict) -> list:
    """Run the node's optional 'verify' shell commands. Returns failure messages (empty = pass)."""
    failures = []
    for cmd in node.get("verify") or []:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            output = (result.stderr or result.stdout).strip()[-500:]
            failures.append(f"  $ {cmd}\n  exit {result.returncode}: {output}")
    return failures


# ── Status propagation ────────────────────────────────────────────────────────


def propagate_completion(node_id: str, index: dict) -> list:
    """Walk up parent chain; mark each parent complete when all its children are done.
    Stops as soon as a parent has incomplete children — grandparent can't be done if parent isn't."""
    updated = []
    entry = index.get(node_id)
    if not entry:
        return updated
    _, parent_chain = entry
    for parent in reversed(parent_chain):
        children = parent.get("children") or []
        if all(c.get("status") == "complete" for c in children):
            if parent.get("status") != "complete":
                parent["status"] = "complete"
                updated.append(parent["id"])
        else:
            break
    return updated


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_next(args):
    tree_data = load_valid_tree(args.tree)
    index = build_index(tree_data["tree"])
    proof_node, proof_result = proof_selection(tree_data, index)
    if proof_result is not None:
        proof_result["execution_strategy"] = execution_strategy(tree_data)
        print(json.dumps(proof_result, indent=2))
        return
    node = proof_node or find_next_leaf(tree_data["tree"], index)

    if node is None:
        print(
            json.dumps(
                {
                    "status": "no_executable_leaves",
                    "message": "All leaves complete, blocked, or decomposed.",
                    "execution_strategy": execution_strategy(tree_data),
                }
            )
        )
        return

    _, parent_chain = index[node["id"]]
    output = {
        **{k: v for k, v in node.items() if k != "children"},
        "parent_intent": parent_chain[-1].get("objective") if parent_chain else None,
        "depth": len(parent_chain),
        "context_file": str(args.tree.parent / "context.md"),
        "execution_strategy": execution_strategy(tree_data),
    }
    proof = active_proof_slice(tree_data)
    if proof is not None:
        output["proof_slice"] = {
            key: proof[key]
            for key in (
                "id",
                "objective",
                "hypothesis",
                "acceptance_criteria",
                "status",
            )
        }
    print(json.dumps(output, indent=2))


def cmd_show(args):
    tree_data = load_valid_tree(args.tree)
    node, parent_chain = find_node(tree_data, args.id)
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    output = {
        "node": node,
        "parent_chain": [
            {
                "id": p["id"],
                "type": p["type"],
                "title": p["title"],
                "objective": p.get("objective"),
            }
            for p in parent_chain
        ],
        "context_file": str(args.tree.parent / "context.md"),
    }
    print(json.dumps(output, indent=2))


def cmd_done(args):
    tree_data = load_valid_tree(args.tree)
    index = build_index(tree_data["tree"])
    node, _ = index.get(args.id, (None, []))
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    if node.get("status") == "complete":
        print(json.dumps({"already_complete": args.id}))
        return
    assert_proof_allows(tree_data, args.id)
    if node.get("status") not in ("pending", "ready", "in_progress"):
        sys.exit(
            f"Error: node '{args.id}' cannot be completed from status '{node.get('status')}'."
        )
    dependencies = incomplete_dependencies(node, index)
    if dependencies:
        sys.exit(
            f"Error: node '{args.id}' has incomplete dependencies: {', '.join(dependencies)}."
        )
    incomplete = [
        c["id"] for c in node.get("children") or [] if c.get("status") != "complete"
    ]
    if incomplete:
        sys.exit(
            f"Error: '{args.id}' has incomplete children: {', '.join(incomplete)}. "
            f"Complete them first — 'done' propagates upward automatically."
        )
    failures = run_verify(node)
    # meta.verify: project-wide regression gate (full suite, lint, ...) run on every done
    failures += run_verify({"verify": tree_data.get("meta", {}).get("verify")})
    if failures:
        sys.exit(f"Error: verify failed for '{args.id}':\n" + "\n".join(failures))

    proof = active_proof_slice(tree_data)
    verifies_proof = False
    if proof is not None and args.id in proof["nodes"]:
        other_incomplete = [
            node_id
            for node_id in proof["nodes"]
            if node_id != args.id
            and index[node_id][0].get("status") != "complete"
        ]
        verifies_proof = not other_incomplete
        if verifies_proof:
            proof_failures = run_verify(proof)
            if proof_failures:
                sys.exit(
                    f"Error: proof slice verify failed for '{proof['id']}':\n"
                    + "\n".join(proof_failures)
                )

    node["status"] = "complete"
    propagated = propagate_completion(args.id, index)
    output = {"marked_complete": args.id, "propagated_complete": propagated}
    if verifies_proof:
        proof["status"] = "verified"
        proof["verified_at"] = datetime.now(timezone.utc).isoformat()
        output.update(
            {
                "status": "awaiting_proof_approval",
                "proof_slice": proof["id"],
                "proof_slice_status": "verified",
            }
        )
    save_tree(tree_data, args.tree)
    print(json.dumps(output))


def cmd_start(args):
    tree_data = load_valid_tree(args.tree)
    index = build_index(tree_data["tree"])
    node, _ = index.get(args.id, (None, []))
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    assert_proof_allows(tree_data, args.id)
    if not is_leaf(node):
        sys.exit(f"Error: node '{args.id}' is not an executable leaf.")
    if node.get("status") not in ("pending", "ready"):
        sys.exit(
            f"Error: node '{args.id}' cannot be started from status '{node.get('status')}'."
        )
    dependencies = incomplete_dependencies(node, index)
    if dependencies:
        sys.exit(
            f"Error: node '{args.id}' has incomplete dependencies: {', '.join(dependencies)}."
        )
    node["status"] = "in_progress"
    save_tree(tree_data, args.tree)
    print(json.dumps({"started": args.id}))


def cmd_block(args):
    tree_data = load_valid_tree(args.tree)
    node, _ = find_node(tree_data, args.id)
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    node["status"] = "blocked"
    if args.reason:
        node["notes"] = args.reason
    save_tree(tree_data, args.tree)
    print(json.dumps({"blocked": args.id, "reason": args.reason}))


def cmd_decompose(args):
    """Mark a leaf as decomposed. The AI then edits tree.yaml to add children, then runs validate."""
    tree_data = load_valid_tree(args.tree)
    node, _ = find_node(tree_data, args.id)
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    node["status"] = "decomposed"
    save_tree(tree_data, args.tree)
    print(
        json.dumps(
            {
                "decomposed": args.id,
                "next_step": (
                    f"Edit {args.tree} to add 'children' under '{args.id}' "
                    f"using the schema in .wbs/node-template.yaml, then run 'wbs.py validate'."
                ),
            }
        )
    )


def cmd_status(args):
    tree_data = load_valid_tree(args.tree)
    index = build_index(tree_data["tree"])

    total = len(index)
    by_status: dict = {}
    for node, _ in index.values():
        s = node.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1

    complete = by_status.get("complete", 0)
    pct = round(complete / total * 100) if total else 0
    proof_node, proof_result = proof_selection(tree_data, index)
    next_node = proof_node or (
        None if proof_result is not None else find_next_leaf(tree_data["tree"], index)
    )

    proof = tree_data.get("proof_slice")
    proof_status = None
    if proof is not None:
        proof_status = {
            "id": proof["id"],
            "status": proof["status"],
            "enforced": active_proof_slice(tree_data) is not None,
            "complete": sum(
                index[node_id][0].get("status") == "complete"
                for node_id in proof["nodes"]
            ),
            "total": len(proof["nodes"]),
        }

    print(
        json.dumps(
            {
                "project": tree_data.get("meta", {}).get("project", "unknown"),
                "execution_strategy": execution_strategy(tree_data),
                "total_nodes": total,
                "complete": complete,
                "completion_pct": pct,
                "by_status": by_status,
                "next": next_node["id"] if next_node else None,
                "scheduler_status": (
                    proof_result["status"]
                    if proof_result
                    else ("ready" if next_node else "no_executable_leaves")
                ),
                "proof_slice": proof_status,
            },
            indent=2,
        )
    )


def cmd_validate(args):
    tree_data = load_tree(args.tree)
    errors, index = validate_tree_data(tree_data)

    result = {"valid": len(errors) == 0, "nodes_checked": len(index), "errors": errors}
    print(json.dumps(result, indent=2))
    if errors:
        sys.exit(1)


def cmd_strategy(args):
    tree_data = load_tree(args.tree)
    meta = tree_data.get("meta")
    if not isinstance(meta, dict):
        sys.exit("Error: top-level 'meta' must be a mapping.")

    if args.name is None:
        errors, _ = validate_tree_data(tree_data)
        if errors:
            sys.exit("Error: tree validation failed:\n- " + "\n- ".join(errors))
        configured = meta.get("execution_strategy")
        print(
            json.dumps(
                {
                    "execution_strategy": execution_strategy(tree_data),
                    "source": "meta" if configured is not None else "default",
                },
                indent=2,
            )
        )
        return

    previous = execution_strategy(tree_data)
    meta["execution_strategy"] = args.name
    errors, _ = validate_tree_data(tree_data)
    if errors:
        sys.exit("Error: tree validation failed:\n- " + "\n- ".join(errors))
    save_tree(tree_data, args.tree)
    print(
        json.dumps(
            {
                "execution_strategy": args.name,
                "previous_execution_strategy": previous,
                "source": "meta",
            },
            indent=2,
        )
    )


def cmd_approve_proof(args):
    tree_data = load_valid_tree(args.tree)
    proof = tree_data.get("proof_slice")
    if proof is None:
        sys.exit("Error: tree has no proof_slice to approve.")
    if proof.get("status") == "approved":
        print(
            json.dumps(
                {
                    "already_approved": proof["id"],
                    "approved_at": proof.get("approved_at"),
                }
            )
        )
        return
    if proof.get("status") != "verified":
        sys.exit(
            f"Error: proof slice '{proof['id']}' must be verified before approval."
        )

    failures = run_verify(proof)
    if failures:
        sys.exit(
            f"Error: proof slice verify failed for '{proof['id']}':\n"
            + "\n".join(failures)
        )

    approved_at = datetime.now(timezone.utc).isoformat()
    proof["status"] = "approved"
    proof["approved_at"] = approved_at
    save_tree(tree_data, args.tree)
    print(
        json.dumps(
            {
                "approved_proof": proof["id"],
                "proof_slice_status": "approved",
                "approved_at": approved_at,
            }
        )
    )


def cmd_init(args):
    prd_path = Path(args.prd)
    if not prd_path.exists():
        sys.exit(f"Error: PRD file '{args.prd}' not found.")

    wbs_dir = args.tree.parent
    wbs_dir.mkdir(parents=True, exist_ok=True)

    if args.tree.exists():
        sys.exit(f"Error: {args.tree} already exists. Delete it to reinitialize.")

    template_path = wbs_dir / "node-template.yaml"
    if not template_path.exists():
        if not DEFAULT_NODE_TEMPLATE.exists():
            sys.exit(
                "Error: node template is missing from the WBS toolkit at "
                f"'{DEFAULT_NODE_TEMPLATE}'. Reinstall the complete toolkit distribution."
            )
        shutil.copyfile(DEFAULT_NODE_TEMPLATE, template_path)

    skeleton = {
        "meta": {
            "project": prd_path.stem,
            "version": "0.1.0",
            "prd_source": str(prd_path),
            "execution_strategy": DEFAULT_EXECUTION_STRATEGY,
            "tech_stack": [],
            "conventions": "See .wbs/context.md",
        },
        "tree": {
            "id": "ROOT",
            "type": "product",
            "title": f"[Populate from {prd_path.name}]",
            "objective": "[PRD skill fills this in]",
            "source_requirements": [],
            "status": "pending",
            "inputs": [str(prd_path)],
            "constraints": [],
            "outputs": [],
            "acceptance_criteria": [],
            "dependencies": [],
            "children": [],
        },
    }
    save_tree(skeleton, args.tree)

    context_path = wbs_dir / "context.md"
    if not context_path.exists():
        context_path.write_text(
            f"# Project Context\n\n"
            f"Source PRD: `{prd_path}`\n\n"
            f"## Outcome Requirements\n\n"
            f"[Fill in: REQ ID, actor, trigger, observable result, evidence, failure behavior, priority, constraints, and assumptions]\n\n"
            f"## Tech Stack\n\n[Fill in]\n\n"
            f"## Conventions\n\n[Fill in]\n\n"
            f"## Delivery Branches\n\n"
            f"[Derived by the PRD writer: requirement mapping, tracer, interfaces, and maturity]\n\n"
            f"## Architecture Notes\n\n[Fill in]\n\n"
            f"## Open Questions\n\n[Fill in]\n\n"
            f"## Non-Functional Requirements\n\n[Fill in: performance targets, security, compliance]\n"
        )

    print(
        json.dumps(
            {
                "initialized": str(args.tree),
                "context_file": str(context_path),
                "schema_template": str(template_path),
                "next_step": "Run the PRD skill/agent to populate tree.yaml, or edit it manually using .wbs/node-template.yaml as the schema reference.",
                "note": "Skeleton will not pass 'wbs.py validate' until fully populated — that is expected.",
            },
            indent=2,
        )
    )


# ── CLI entry point ───────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="wbs.py",
        description="WBS — Recursive Work Breakdown Structure manager for AI-driven development.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Successful output is JSON. Validation reports use stdout; "
            "operational errors use stderr."
        ),
    )
    parser.add_argument(
        "--tree",
        type=Path,
        default=DEFAULT_TREE,
        metavar="PATH",
        help=f"Path to tree.yaml [default: {DEFAULT_TREE}]",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("next", help="Next executable leaf (JSON)")

    p = sub.add_parser("show", help="Node + parent chain (JSON)")
    p.add_argument("id", help="Node ID")

    p = sub.add_parser("done", help="Mark node complete, propagate upward")
    p.add_argument("id", help="Node ID")

    p = sub.add_parser("start", help="Mark node in_progress")
    p.add_argument("id", help="Node ID")

    p = sub.add_parser("block", help="Mark node blocked")
    p.add_argument("id", help="Node ID")
    p.add_argument("--reason", help="Reason for blocking")

    p = sub.add_parser(
        "decompose",
        help="Mark leaf decomposed; edit tree.yaml to add children, then validate",
    )
    p.add_argument("id", help="Node ID")

    p = sub.add_parser("strategy", help="Show or persist the execution strategy")
    p.add_argument(
        "name",
        nargs="?",
        choices=sorted(VALID_EXECUTION_STRATEGIES),
        help="Strategy to persist; omit to show the effective strategy",
    )

    sub.add_parser("status", help="Progress dashboard")
    sub.add_parser("validate", help="Validate tree.yaml schema and integrity")
    sub.add_parser(
        "approve-proof",
        help="Approve a verified proof slice and unlock ordinary traversal",
    )

    p = sub.add_parser("init", help="Scaffold .wbs/tree.yaml from a PRD file")
    p.add_argument("prd", help="Path to PRD markdown file")

    args = parser.parse_args()
    dispatch = {
        "next": cmd_next,
        "show": cmd_show,
        "done": cmd_done,
        "start": cmd_start,
        "block": cmd_block,
        "decompose": cmd_decompose,
        "strategy": cmd_strategy,
        "status": cmd_status,
        "validate": cmd_validate,
        "approve-proof": cmd_approve_proof,
        "init": cmd_init,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

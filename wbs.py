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
  status                Progress dashboard
  validate              Validate tree.yaml schema and integrity
  init <prd.md>         Scaffold .wbs/tree.yaml from PRD (PRD skill populates the real content)

Options:
  --tree PATH           Path to tree.yaml [default: .wbs/tree.yaml]

All commands emit JSON to stdout. Errors go to stderr with non-zero exit.
Run with: python wbs.py <command> or uv run wbs.py <command>
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_TREE = Path(".wbs/tree.yaml")

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
REQUIRED_FIELDS = ("id", "type", "title", "objective", "status")


# ── Tree I/O ──────────────────────────────────────────────────────────────────


def load_tree(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"Error: {path} not found. Run 'wbs.py init <prd.md>' first.")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "tree" not in data:
        sys.exit(f"Error: {path} must contain a 'tree' key at the top level.")
    return data


def save_tree(data: dict, path: Path) -> None:
    with open(path, "w") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )


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
    tree_data = load_tree(args.tree)
    index = build_index(tree_data["tree"])
    node = find_next_leaf(tree_data["tree"], index)

    if node is None:
        print(
            json.dumps(
                {
                    "status": "no_executable_leaves",
                    "message": "All leaves complete, blocked, or decomposed.",
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
    }
    print(json.dumps(output, indent=2))


def cmd_show(args):
    tree_data = load_tree(args.tree)
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
    tree_data = load_tree(args.tree)
    node, _ = find_node(tree_data, args.id)
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    if node.get("status") == "complete":
        print(json.dumps({"already_complete": args.id}))
        return
    incomplete = [
        c["id"] for c in node.get("children") or [] if c.get("status") != "complete"
    ]
    if incomplete:
        sys.exit(
            f"Error: '{args.id}' has incomplete children: {', '.join(incomplete)}. "
            f"Complete them first — 'done' propagates upward automatically."
        )
    failures = run_verify(node)
    if failures:
        sys.exit(f"Error: verify failed for '{args.id}':\n" + "\n".join(failures))
    node["status"] = "complete"
    index = build_index(tree_data["tree"])
    propagated = propagate_completion(args.id, index)
    save_tree(tree_data, args.tree)
    print(json.dumps({"marked_complete": args.id, "propagated_complete": propagated}))


def cmd_start(args):
    tree_data = load_tree(args.tree)
    node, _ = find_node(tree_data, args.id)
    if node is None:
        sys.exit(f"Error: node '{args.id}' not found.")
    node["status"] = "in_progress"
    save_tree(tree_data, args.tree)
    print(json.dumps({"started": args.id}))


def cmd_block(args):
    tree_data = load_tree(args.tree)
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
    tree_data = load_tree(args.tree)
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
    tree_data = load_tree(args.tree)
    index = build_index(tree_data["tree"])

    total = len(index)
    by_status: dict = {}
    for node, _ in index.values():
        s = node.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1

    complete = by_status.get("complete", 0)
    pct = round(complete / total * 100) if total else 0
    next_node = find_next_leaf(tree_data["tree"], index)

    print(
        json.dumps(
            {
                "project": tree_data.get("meta", {}).get("project", "unknown"),
                "total_nodes": total,
                "complete": complete,
                "completion_pct": pct,
                "by_status": by_status,
                "next": next_node["id"] if next_node else None,
            },
            indent=2,
        )
    )


def cmd_validate(args):
    tree_data = load_tree(args.tree)
    errors = []

    if "meta" not in tree_data:
        errors.append("Missing top-level 'meta' section.")

    index = build_index(tree_data["tree"])

    # Duplicate IDs — must walk the raw tree; build_index silently overwrites dupes
    seen: set = set()

    def check_dupes(node):
        if node["id"] in seen:
            errors.append(f"Duplicate node ID: '{node['id']}'")
        seen.add(node["id"])
        for child in node.get("children") or []:
            check_dupes(child)

    check_dupes(tree_data["tree"])

    for node_id, (node, _) in index.items():
        # Required fields
        for field in REQUIRED_FIELDS:
            if field not in node:
                errors.append(f"{node_id}: missing required field '{field}'")

        # Valid enum values
        if node.get("type") not in VALID_TYPES:
            errors.append(
                f"{node_id}: invalid type '{node.get('type')}' — must be one of {sorted(VALID_TYPES)}"
            )
        if node.get("status") not in VALID_STATUSES:
            errors.append(
                f"{node_id}: invalid status '{node.get('status')}' — must be one of {sorted(VALID_STATUSES)}"
            )

        # Leaf nodes must have at least one acceptance criterion
        if is_leaf(node) and node.get("status") != "decomposed":
            if not node.get("acceptance_criteria"):
                errors.append(
                    f"{node_id}: leaf node missing 'acceptance_criteria' — add at least one verifiable condition"
                )

        # Dependency resolution
        for dep in node.get("dependencies") or []:
            dep_id = dep if isinstance(dep, str) else dep.get("id", "")
            dep_type = None if isinstance(dep, str) else dep.get("type")
            if dep_id not in index:
                errors.append(f"{node_id}: dependency '{dep_id}' not found in tree")
            if dep_type and dep_type not in VALID_DEP_TYPES:
                errors.append(
                    f"{node_id}: dependency type '{dep_type}' invalid — must be one of {sorted(VALID_DEP_TYPES)}"
                )

    # Dependency cycles — includes implicit parent→child edges, so a node
    # depending on its own ancestor is caught (ancestor can't complete first)
    graph: dict = {}
    for node_id, (node, _) in index.items():
        edges = [c["id"] for c in node.get("children") or []]
        for dep in node.get("dependencies") or []:
            dep_id = dep if isinstance(dep, str) else dep.get("id", "")
            if dep_id in index:
                edges.append(dep_id)
        graph[node_id] = edges

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)

    def find_cycle(nid, path):
        color[nid] = GRAY
        path.append(nid)
        for nxt in graph[nid]:
            if color[nxt] == GRAY:
                cycle = path[path.index(nxt) :] + [nxt]
                errors.append(f"Dependency cycle: {' -> '.join(cycle)}")
                path.pop()
                color[nid] = BLACK
                return True
            if color[nxt] == WHITE and find_cycle(nxt, path):
                path.pop()
                color[nid] = BLACK
                return True
        path.pop()
        color[nid] = BLACK
        return False

    for nid in graph:
        if color[nid] == WHITE and find_cycle(nid, []):
            break  # ponytail: report first cycle only; fix and re-validate

    result = {"valid": len(errors) == 0, "nodes_checked": len(index), "errors": errors}
    print(json.dumps(result, indent=2))
    if errors:
        sys.exit(1)


def cmd_init(args):
    prd_path = Path(args.prd)
    if not prd_path.exists():
        sys.exit(f"Error: PRD file '{args.prd}' not found.")

    wbs_dir = args.tree.parent
    wbs_dir.mkdir(parents=True, exist_ok=True)

    if args.tree.exists():
        sys.exit(f"Error: {args.tree} already exists. Delete it to reinitialize.")

    skeleton = {
        "meta": {
            "project": prd_path.stem,
            "version": "0.1.0",
            "prd_source": str(prd_path),
            "tech_stack": [],
            "conventions": "See .wbs/context.md",
        },
        "tree": {
            "id": "ROOT",
            "type": "product",
            "title": f"[Populate from {prd_path.name}]",
            "objective": "[PRD skill fills this in]",
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
            f"## Tech Stack\n\n[Fill in]\n\n"
            f"## Conventions\n\n[Fill in]\n\n"
            f"## Architecture Notes\n\n[Fill in]\n\n"
            f"## Non-Functional Requirements\n\n[Fill in: performance targets, security, compliance]\n"
        )

    print(
        json.dumps(
            {
                "initialized": str(args.tree),
                "context_file": str(context_path),
                "schema_template": str(wbs_dir / "node-template.yaml"),
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
        epilog="All output is JSON. Errors go to stderr with non-zero exit.",
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

    sub.add_parser("status", help="Progress dashboard")
    sub.add_parser("validate", help="Validate tree.yaml schema and integrity")

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
        "status": cmd_status,
        "validate": cmd_validate,
        "init": cmd_init,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

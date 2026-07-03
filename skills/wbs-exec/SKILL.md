---
name: wbs-exec
description: Use this skill to execute a WBS tree — implementing work packages from .wbs/tree.yaml as tested code, one leaf at a time. Triggers on: "implement the next node", "run the wbs", "execute the tree", "work the tree", "build the next work package", "wbs next", "keep implementing", or any request to turn an existing .wbs/ spec into code. Requires .wbs/tree.yaml (created by the wbs-prd skill); if missing, suggest /wbs-prd first.
---

## Gotchas

- `--tree` is a global flag: `wbs.py --tree path/tree.yaml next`, not after the subcommand.
- `wbs.py done` runs the node's `verify` commands AND `meta.verify` (project-wide gate). If it refuses, fix the code — never weaken or delete a verify command. Correcting a verify entry's *path* to where the tests actually live is fine; changing what it checks is not.
- Spec-time `verify` entries reference test files that don't exist yet. That's the gate working: write the tests, then `done`.
- context.md's `## Design Alternatives` lists pruned paths. Do not re-litigate or implement them, even if one looks better mid-implementation — if you genuinely hit a wall, `block` the node with the reason instead.
- If an acceptance criterion cannot be turned into a test, do NOT guess or skip it: `wbs.py block <id> --reason "untestable AC: ..."` and tell the user. Ambiguity caught before code is a spec fix; caught after, it's rework.
- Use `block` only for genuine external blockers. Work awaiting review is `in_progress`, not `blocked`.
- A leaf too large for one session is not a failure: `wbs.py decompose <id>`, add children to tree.yaml, `validate`, continue.

## The loop

Repeat until `next` returns `no_executable_leaves` or the user stops you:

1. **Load** — `wbs.py next`. Read `context_file` (always). For nodes at depth ≥ 3, run `wbs.py show <id>` for the full ancestry — `next` only gives the immediate parent's intent. `wbs.py start <id>`.
2. **Tests first** — translate every `acceptance_criteria` item into a failing test before writing any implementation. One test per criterion, minimum; add edge cases the criteria imply. Put them where context.md's test-file convention says — matching the node's `verify` command path. Run them; confirm they fail for the right reason.
3. **Implement** — the minimum code that turns the tests green, honoring the node's `constraints` and context.md conventions. `outputs` is the node's interface: build exactly that surface, hide everything else.
4. **Gate** — run the full Definition-of-Done commands from context.md (suite, lint, typecheck) yourself before calling done, so failures surface with full output in your session rather than truncated in the done error.
5. **Close** — `wbs.py done <id>`. If it refuses, fix and retry. Then report: node ID, what was built, test count, anything learned that belongs in context.md's `## Learnings`.

## Capability checkpoint

When `done` propagates completion to a `CAP-*` node, pause before the next leaf and run an integrity pass over that capability's code: does every module map to a `## Core Design Concepts` entry in context.md? Do the interfaces match the declared `outputs`? Report drift to the user — with a proposed fix — before continuing. This is the one review point; don't review per leaf.

## Co-evolution

Implementation teaches things the spec couldn't know. When a node reveals a wrong assumption, a missing dependency, or a problem reframing: append a dated entry to context.md `## Learnings`, and if the tree itself is wrong (missing node, wrong boundary), propose the tree edit to the user — don't silently restructure. After manual tree edits, always `wbs.py validate`.

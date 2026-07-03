# recursive-development

A recursive Work Breakdown Structure (WBS) system for AI-driven software development.

Every node in the tree — from the top-level product down to a single work package — uses the same self-similar schema. Development becomes a depth-first, bottom-up traversal of that tree, with each leaf executed by an AI agent (Claude Code, Codex, or any AI coder).

---

## Core idea

A PRD decomposes an app into a tree of work. Each node answers three questions:

1. **What must be delivered?**
2. **What child units fully cover this scope?**
3. **Is this node executable yet?**

The recursion stops when a node is small enough for a single AI agent session. The AI reads the leaf, implements it, marks it done. Completion propagates upward automatically.

---

## Installation

**Skills:** Copy `skills/wbs-prd/` and `skills/wbs-exec/` to `~/.claude/skills/`, or symlink:

```bash
ln -s /path/to/recursive-development/skills/wbs-prd ~/.claude/skills/
ln -s /path/to/recursive-development/skills/wbs-exec ~/.claude/skills/
```

## Quick start

**Requires:** Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) (or `pip install pyyaml`)

```bash
# 1. Spec a project via the wbs-prd Claude Code skill
/wbs-prd          # interviews you, writes .wbs/tree.yaml + .wbs/context.md

# 2. Get the next executable leaf
uv run wbs.py next

# 3. Implement the leaf (AI reads the JSON output and acts)

# 4. Mark it done — completion propagates up automatically
uv run wbs.py done <node-id>

# 5. Repeat
uv run wbs.py next
```

If a leaf is too large for one session:
```bash
uv run wbs.py decompose <node-id>
# Edit .wbs/tree.yaml to add children under that node
uv run wbs.py validate
uv run wbs.py next   # now returns one of the children
```

---

## Commands

`--tree PATH` is a global flag that goes **before** the subcommand (default: `.wbs/tree.yaml`).

| Command | Description |
|---|---|
| `wbs.py next` | Next executable leaf as JSON — respects dependency order |
| `wbs.py show <id>` | Full node + parent chain as JSON — load into agent context |
| `wbs.py done <id>` | Mark complete; propagates status up the tree |
| `wbs.py start <id>` | Mark `in_progress` |
| `wbs.py block <id> [--reason "..."]` | Mark `blocked` |
| `wbs.py decompose <id>` | Mark for re-expansion; edit tree, then validate |
| `wbs.py status` | Progress dashboard (total nodes, % complete, next leaf) |
| `wbs.py validate` | Schema + integrity check — run after any manual tree edit |
| `wbs.py init <prd.md>` | Scaffold a skeleton `.wbs/tree.yaml` from a PRD file |

---

## File layout

```
.wbs/
  tree.yaml           # the WBS tree — spec + live status in one file
  context.md          # project context loaded by the AI with every leaf
  node-template.yaml  # schema reference for humans and the PRD skill
wbs.py                # the CLI tool
```

See the [User Guide](docs/user-guide.md) for the full node schema, the wbs-prd skill workflow, dependency types, and examples.

---

## Node hierarchy

```
product
  └── capability        (CAP-{DOMAIN})
        └── feature     ({DOMAIN}-{FEATURE})
              └── module            ({DOMAIN}-{FEATURE}-{MODULE})
                    └── work_package  ({DOMAIN}-{FEATURE}-{UNIT})  ← leaf
                          └── task / step   (added at execution time)
```

The PRD skill generates down to `work_package`. Task and step nodes are added on demand via `wbs.py decompose` during execution.

---

## The wbs-prd skill

Install location: `~/.claude/skills/wbs-prd/`

Trigger in Claude Code with any of: `"spec this out"`, `"plan this"`, `"I want to build"`, `"grill me on this"`, `"PRD this"`, `"generate the WBS"`, `"create the tree"`.

The skill interviews you (one question at a time, always gives a recommended answer) then writes `.wbs/tree.yaml` and `.wbs/context.md` ready for execution.

---

## Output contract

All `wbs.py` commands emit JSON to stdout. Errors go to stderr with a non-zero exit code. This makes every command scriptable and AI-readable.

Example `next` output:
```json
{
  "id": "AUTH-MAGICLINK-API",
  "type": "work_package",
  "title": "Magic-link request endpoint",
  "objective": "Accept an email and issue a short-lived signed login token",
  "inputs": ["User model (AUTH-USER-REPO)"],
  "constraints": ["Stateless API", "Token expiry: 15 minutes"],
  "outputs": ["POST /auth/magic-link", "Token stored in Redis"],
  "acceptance_criteria": ["Invalid email → 422", "Valid request → 200"],
  "dependencies": [{"id": "AUTH-USER-REPO", "type": "data"}],
  "parent_intent": "Secure, passwordless client login with no IT support burden",
  "depth": 2,
  "context_file": ".wbs/context.md"
}
```

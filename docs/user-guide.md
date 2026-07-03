# User Guide — recursive-development

> The parent defines intent. The children define composition. The leaves define execution.

---

## Contents

1. [How the system works](#how-the-system-works)
2. [The node schema](#the-node-schema)
3. [The wbs-prd skill — speccing a project](#the-wbs-prd-skill--speccing-a-project)
4. [The execution loop](#the-execution-loop)
5. [Dependency types](#dependency-types)
6. [Re-decomposition](#re-decomposition)
7. [wbs.py command reference](#wbspy-command-reference)
8. [Validation rules](#validation-rules)
9. [context.md — the executor's briefing file](#contextmd--the-executors-briefing-file)
10. [Tips for AI agents](#tips-for-ai-agents)
11. [Working with multi-tree systems](#working-with-multi-tree-systems)

---

## How the system works

The system treats software development as a recursive Work Breakdown Structure. Every node — from the top-level product down to a single work package — uses the same schema and answers the same three questions:

1. **What must be delivered?** (`objective`, `outputs`, `acceptance_criteria`)
2. **What child units fully cover this scope?** (`children`)
3. **Is this node executable yet?** (is it a leaf? are all dependencies complete?)

The tree is stored in `.wbs/tree.yaml`. `wbs.py` manages tree state — it finds the next executable leaf, records completion, propagates status upward, and validates the schema. The AI agent (Claude Code, Codex, or any coder) reads the leaf context and implements it.

### Hierarchy

```
product                  ← ROOT — the full system
  capability             ← CAP-{DOMAIN} — a major independent deliverable domain
    feature              ← {DOMAIN}-{FEATURE} — a user-facing capability within a domain
      module             ← {DOMAIN}-{FEATURE}-{MODULE} — an architectural component
        work_package     ← {DOMAIN}-{FEATURE}-{UNIT} — a discrete, implementable unit (leaf)
          task           ← added at execution time via decompose
            step         ← the atomic operation
```

**The PRD skill generates down to `work_package`.** Task and step nodes are added during execution if a work package turns out to be too large for one agent session.

### Status lifecycle

```
pending → ready → in_progress → complete
                              ↘ blocked
         decomposed           (was a leaf, now has children)
```

`wbs.py next` only returns nodes with status `pending` or `ready` whose dependencies are all `complete`. `wbs.py done` marks a node `complete` and walks up the parent chain, marking any parent whose children are all complete.

---

## The node schema

Every node at every level uses this exact structure. The tree is self-similar.

```yaml
id: AUTH-MAGICLINK-API          # UPPER-KEBAB. Convention: see hierarchy above.
type: work_package              # product|capability|feature|module|work_package|task|step
title: "Build magic-link request endpoint"
objective: "Accept email and issue a signed short-lived login token"
status: pending                 # pending|ready|in_progress|complete|blocked|decomposed

inputs:                         # What this node needs before it can start
  - "User model (AUTH-USER-REPO)"

constraints:                    # Functional rules — NOT tech stack (that goes in context.md)
  - "Stateless API — no session stored server-side"
  - "Token expiry: 15 minutes"
  - "Rate limit: 5 requests per email per hour"

outputs:                        # Concrete deliverables
  - "POST /auth/magic-link endpoint"
  - "Signed token stored in Redis with TTL"

acceptance_criteria:            # Verifiable conditions for done — required on every leaf
  - "Invalid email format → 422"
  - "Valid request → 200, email dispatched (mocked in tests)"
  - "Token stored in Redis with 15-minute TTL"
  - "6th request within 1 hour → 429"

verify:                         # Optional. Shell commands run by `done` — all must
  - "pytest tests/auth -q"      # exit 0 or the node is refused completion.

dependencies:                   # Must be complete before this node is executable
  - id: AUTH-USER-REPO
    type: data                  # data | sequence | runtime (see Dependency types)

owner: null                     # Team/role, or null
agent_type: api_builder         # architect|api_builder|ui_builder|test_writer|docs_writer|deployer
effort_estimate: "1d"           # null, "2h", "1d", "3d"
notes: null                     # Open questions, late-discovered constraints

children: []                    # Empty = leaf. Add child nodes (same schema) after decompose.
```

### Required fields

`id`, `type`, `title`, `objective`, `status` — every node.

`acceptance_criteria` (non-empty) — every leaf node (non-decomposed, no children).

### ID conventions

| Level | Pattern | Example |
|---|---|---|
| product | `ROOT` | `ROOT` |
| capability | `CAP-{DOMAIN}` | `CAP-AUTH` |
| feature | `{DOMAIN}-{FEATURE}` | `AUTH-MAGICLINK` |
| module | `{DOMAIN}-{FEATURE}-{MODULE}` | `AUTH-MAGICLINK-TOKENS` |
| work_package | `{DOMAIN}-{FEATURE}-{UNIT}` | `AUTH-MAGICLINK-API` |

---

## The wbs-prd skill — speccing a project

The `wbs-prd` skill generates `.wbs/tree.yaml` and `.wbs/context.md` from a structured interview.

**Install location:** `~/.claude/skills/wbs-prd/`

**Trigger phrases:** `"spec this out"`, `"plan this"`, `"I want to build"`, `"grill me on this"`, `"PRD this"`, `"generate the WBS"`, `"create the tree"`, `"scaffold the tree"`, `"let's plan before we build"`

### What the interview covers

The skill interviews you in hierarchy order:

1. **Scope** — single-sentence objective, user types, what's out of scope, definition of done at the top level
2. **Capabilities** — the 3–7 major independently-deliverable domains
3. **Features** — what makes up each capability, which features depend on others
4. **Work packages** — discrete deliverables within each feature (endpoints, models, UI components, test suites)
5. **Implementation context** — tech stack, non-functional requirements, external integrations, conventions

**One question at a time. The skill always gives a recommended answer for you to accept or redirect.** If a question can be answered by reading the codebase, the skill reads the codebase instead of asking.

### What it produces

After the interview, the skill writes:

- **`.wbs/tree.yaml`** — the complete WBS tree, status `pending` on all nodes, decomposed to `work_package` level
- **`.wbs/context.md`** — tech stack, conventions, architecture notes, NFRs — loaded by the AI executor with every leaf

Then runs `wbs.py validate` and `wbs.py status` so you see the result before execution starts.

---

## The execution loop

```bash
# Get the next leaf — dependency order is enforced automatically
uv run wbs.py next

# (AI reads the JSON output, loads context.md, implements the leaf)

# For deep trees: get the full parent chain for more context
uv run wbs.py show AUTH-MAGICLINK-API

# Mark done — propagates upward
uv run wbs.py done AUTH-MAGICLINK-API

# Check progress
uv run wbs.py status

# Next iteration
uv run wbs.py next
```

### What `next` returns

`next` returns the leaf with the highest priority in a depth-first left-to-right traversal where all dependencies are met:

```json
{
  "id": "AUTH-USER-REPO",
  "type": "work_package",
  "title": "User repository",
  "objective": "Persist and retrieve client accounts by email",
  "inputs": [],
  "constraints": ["Email must be unique per tenant"],
  "outputs": ["User model", "get_by_email()"],
  "acceptance_criteria": [
    "get_by_email returns None for unknown email",
    "Duplicate email within same tenant raises conflict error"
  ],
  "dependencies": [],
  "parent_intent": "Secure, passwordless client login with no IT support burden",
  "depth": 2,
  "context_file": ".wbs/context.md"
}
```

The AI should read `context_file` alongside this output before implementing.

### What `done` does

1. Sets the node's `status` to `complete`
2. Walks up the parent chain
3. Marks each parent `complete` if all its children are `complete`
4. Stops when it reaches a parent with an incomplete child
5. Saves the tree

```json
{
  "marked_complete": "AUTH-USER-REPO",
  "propagated_complete": []
}
```

When the final leaf of a subtree completes, you'll see the cascade:
```json
{
  "marked_complete": "AUTH-MAGICLINK-API",
  "propagated_complete": ["CAP-AUTH", "ROOT"]
}
```

---

## Dependency types

Each dependency entry in a node's `dependencies` list has an `id` and a `type`:

| Type | Meaning | Example |
|---|---|---|
| `data` | This node needs output or data produced by the dependency | API endpoint needs the data model from a repository node |
| `sequence` | This node must start after the dependency completes — ordering only, no data handoff | DB migration must run before seed script |
| `runtime` | Both nodes must be deployed/running together | Frontend needs auth service deployed |

`wbs.py next` treats all three types the same for scheduling: the dependency node must be `complete` before the dependent node is executable. The type is informational for the AI executor — it tells the agent *why* the dependency exists.

---

## Re-decomposition

If `next` returns a node that turns out to be too large for one agent session:

```bash
# 1. Mark it as decomposed
uv run wbs.py decompose AUTH-MAGICLINK-API

# 2. Edit .wbs/tree.yaml to add children under AUTH-MAGICLINK-API
#    Use .wbs/node-template.yaml as the schema reference
#    Children can have their own dependencies on each other

# 3. Validate the updated tree
uv run wbs.py validate

# 4. Resume — next will now return one of the children
uv run wbs.py next
```

A decomposed node is not complete — it's a parent waiting for its children. The original node's `status` becomes `decomposed` and its `acceptance_criteria` transfers to its children (or you refine them).

The system is genuinely recursive: any node at any level can be decomposed at any time. A work package can become a feature. A feature can grow sub-features. The loop is always the same.

---

## wbs.py command reference

**Global flag:** `--tree PATH` — specify an alternative tree file. Goes *before* the subcommand.

```bash
uv run wbs.py --tree path/to/other.yaml validate
```

### `next`

Returns the next executable leaf as JSON. Returns `{"status": "no_executable_leaves"}` when all leaves are complete, blocked, or decomposed.

```bash
uv run wbs.py next
```

### `show <id>`

Returns the full node plus its complete parent chain. Use this when `next` gives you the leaf ID and you want the full ancestry for context.

```bash
uv run wbs.py show AUTH-MAGICLINK-API
```

### `done <id>`

Marks a node complete and propagates upward.

```bash
uv run wbs.py done AUTH-MAGICLINK-API
```

### `start <id>`

Marks a node `in_progress`. Optional — useful for multi-agent coordination.

```bash
uv run wbs.py start AUTH-MAGICLINK-API
```

### `block <id> [--reason "..."]`

Marks a node `blocked`. The reason is stored in the node's `notes` field.

```bash
uv run wbs.py block AUTH-MAGICLINK-API --reason "Waiting on Redis provisioning"
```

A blocked node is skipped by `next`. Unblock by editing `status` back to `pending` in `tree.yaml` and running `validate`.

### `decompose <id>`

Marks a node `decomposed`. The AI then edits `tree.yaml` to add children, then runs `validate`.

```bash
uv run wbs.py decompose AUTH-MAGICLINK-API
```

### `status`

Progress dashboard.

```bash
uv run wbs.py status
# {
#   "project": "client-portal",
#   "total_nodes": 12,
#   "complete": 4,
#   "completion_pct": 33,
#   "by_status": {"complete": 4, "pending": 7, "in_progress": 1},
#   "next": "AUTH-MAGICLINK-VERIFY"
# }
```

### `validate`

Checks the tree against the schema. Exits non-zero if any errors are found.

```bash
uv run wbs.py validate
```

Checks: required fields on all nodes, valid `type` and `status` values, no duplicate IDs, all dependency IDs resolve to real nodes, valid dependency types, non-empty `acceptance_criteria` on all leaf nodes.

Run `validate` after any manual edit to `tree.yaml`.

### `init <prd.md>`

Scaffolds a skeleton `tree.yaml` and `context.md` from an existing PRD file. Intended for when you have a written PRD and want to start the tree structure. The `wbs-prd` skill is the preferred way to generate the tree from scratch via conversation.

```bash
uv run wbs.py init docs/prd.md
```

**Note:** The skeleton will not pass `validate` until fully populated — that is expected.

---

## Validation rules

`wbs.py validate` enforces:

| Rule | Scope |
|---|---|
| Required fields present (`id`, `type`, `title`, `objective`, `status`) | All nodes |
| `type` is one of: `product`, `capability`, `feature`, `module`, `work_package`, `task`, `step` | All nodes |
| `status` is one of: `pending`, `ready`, `in_progress`, `complete`, `blocked`, `decomposed` | All nodes |
| No duplicate node IDs | Whole tree |
| All `dependencies[].id` values resolve to existing nodes | All nodes |
| `dependencies[].type` is one of: `data`, `sequence`, `runtime` | All nodes |
| `acceptance_criteria` list is non-empty | Leaf nodes (not `decomposed`) |

A tree that fails validation will produce incorrect behavior from `next` and `done`. Always fix validation errors before executing.

---

## context.md — the executor's briefing file

`.wbs/context.md` is the project-level context file the AI loads alongside every leaf node. It answers everything the node schema doesn't: what tech stack, what conventions, what architecture decisions, what non-functional constraints.

```markdown
# Project Context

## Tech Stack
- Python 3.12, FastAPI, Pydantic v2
- PostgreSQL 16 (primary store), Redis 7 (cache + token TTLs)
- React 18 + TypeScript, Vite, Tailwind CSS

## Conventions
- API: RESTful, /api/v1/, snake_case JSON
- Tests: pytest + httpx; no DB mocks — use test database
- Errors: RFC 9457 Problem Details format

## Architecture Notes
- Monorepo: backend/, frontend/, infra/
- Multi-tenant: every query scoped by tenant_id from JWT claims

## Non-Functional Requirements
- p95 response time < 200ms under 500 concurrent users
- SOC 2 Type II: PII encrypted at rest, audit log for auth events
```

Keep it dense and factual. No narrative. The AI reads this cold before implementing each leaf.

---

## Tips for AI agents

When using `wbs.py` as part of an agentic loop:

**Always read `context_file` before implementing.** The leaf node JSON includes a `context_file` path. Load it. It has the tech stack and conventions that determine how to implement the node correctly.

**Use `show <id>` for full ancestry.** `next` returns only the immediate parent's intent. For nodes deep in the tree, `show` gives you the full chain from ROOT to leaf — useful for understanding *why* a node exists.

**Run `validate` after editing `tree.yaml`.** Direct edits (during decompose, or to fix a node) can introduce errors. Validate immediately; don't discover the error three nodes later.

**`decompose` before giving up.** If a leaf is too large to complete in one session, call `decompose` and split it. The system is designed for this — it's not a failure, it's the recursion working.

**`block` doesn't complete — don't use it for done.** A blocked node is skipped by `next`. If you've implemented something and it's pending external review, mark it `in_progress`, not `blocked`. Use `block` only for genuine external blockers.

---

## Working with multi-tree systems

Large systems often have cross-cutting concerns — a shared auth library, a shared data model, a mail service — that multiple features depend on. These become their own trees (their own `tree.yaml` files in subdirectories or sibling repos).

The dependency types are designed for this:

- Cross-tree `data` dependency: the dependent work package's `inputs` list names the specific output it needs from the other tree (e.g., `"User model from auth-service"`)
- Cross-tree `sequence` dependency: note the external project and node in `constraints` or `notes`
- Cross-tree `runtime` dependency: note the deployment dependency in `constraints`

For single-repo monorepos, shared concerns are typically capability subtrees within the same `tree.yaml` — the auth capability produces outputs that the portal capability's work packages list as `inputs`. The dependency graph within a single tree handles this cleanly.

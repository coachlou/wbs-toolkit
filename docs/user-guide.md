# User Guide — recursive-development

> The parent defines intent. The children define composition. The leaves define execution.

The normative intake and synthesis boundary is defined in the [Outcome-Driven WBS Specification](outcome-driven-specification.md).

---

## Contents

1. [How the system works](#how-the-system-works)
2. [The node schema](#the-node-schema)
3. [The wbs-prd skill — speccing a project](#the-wbs-prd-skill--speccing-a-project)
4. [The execution loop](#the-execution-loop)
5. [Proof Slice Gate](#proof-slice-gate)
6. [Dependency types](#dependency-types)
7. [Re-decomposition](#re-decomposition)
8. [wbs.py command reference](#wbspy-command-reference)
9. [Validation rules](#validation-rules)
10. [context.md — the executor's briefing file](#contextmd--the-executors-briefing-file)
11. [Tips for AI agents](#tips-for-ai-agents)
12. [Working with multi-tree systems](#working-with-multi-tree-systems)

---

## How the system works

The system treats software development as a recursive Work Breakdown Structure. Every node — from the top-level product down to a single work package — uses the same schema and answers the same three questions:

1. **What must be delivered?** (`objective`, `outputs`, `acceptance_criteria`)
2. **What child units fully cover this scope?** (`children`)
3. **Is this node executable yet?** (is it a leaf? are all dependencies complete?)

The tree is stored in `.wbs/tree.yaml`. `wbs.py` manages tree state — it finds the next executable leaf, records completion, propagates status upward, and validates the schema. The AI agent (Claude Code, Codex, or any coder) reads the leaf context and implements it. The default `proof_slice_first` strategy enforces an optional top-level `proof_slice` when one is declared; that temporary gate is for an architectural proof that crosses delivery-branch ownership boundaries. Without a Proof Slice, ordinary traversal begins immediately.

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

A Proof Slice has its own gate lifecycle:

```text
pending → verified → approved
```

`verified` means its end-to-end commands passed. It does not authorize broader work; `approve-proof` rechecks the evidence and records explicit approval.

---

## The node schema

Every node at every level uses this exact structure. The tree is self-similar.

```yaml
id: AUTH-MAGICLINK-API          # UPPER-KEBAB. Convention: see hierarchy above.
type: work_package              # product|capability|feature|module|work_package|task|step
title: "Build magic-link request endpoint"
objective: "Accept email and issue a signed short-lived login token"
source_requirements: [REQ-001] # Stable outcome IDs from context.md
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

The interview stays in product language:

1. **Purpose and scope** — the problem, actors, successful product result, exclusions, and alternatives
2. **Functional journeys** — what triggers each behavior, what information enters, what changes, and what result the actor observes
3. **Evidence and failures** — what proves each result, material edge cases, and evidence that would invalidate the plan
4. **Priority and boundaries** — required-now, later, and excluded results; sequencing commitments and affected consumers
5. **Operating constraints** — existing systems and contracts, security, performance, compliance, compatibility, and organization-wide quality evidence

The interview does not ask you to define capabilities, delivery branches, work packages, dependencies, tracers, or Proof Slice membership. After you confirm the functionality-and-evidence ledger, the PRD writer derives that representation from the requirements and repository.

**One question at a time. The skill always gives a recommended answer for you to accept or redirect.** If a question can be answered by reading the codebase, the skill reads the codebase instead of asking.

### What it produces

After the interview, the skill writes:

- **`.wbs/tree.yaml`** — the complete WBS tree, status `pending` on all nodes, decomposed to `work_package` level
- **`.wbs/context.md`** — tech stack, conventions, architecture notes, NFRs — loaded by the AI executor with every leaf
- **Requirement traceability** — stable `REQ-*` outcomes in context.md and `source_requirements` mappings on generated nodes
- **Optional `proof_slice`** — only when the minimum architectural proof crosses delivery-branch ownership boundaries; omitted when one branch tracer already supplies the proof

Then runs `wbs.py validate` and `wbs.py status` so you see the result before execution starts.

New trees set `meta.execution_strategy: proof_slice_first`. Existing trees without the field resolve to the same default. Use `wbs.py strategy legacy_bottom_up` only when you deliberately want unrestricted legacy traversal.

### Execution units, delivery units, and proof units

A leaf work package is sized for one agent session. An outcome-bearing feature branch is a larger delivery unit: its implementation leaves can be built bottom-up, but the branch is not empirically integrated until its explicit `*-E2E` tracer leaf passes. The tracer depends on the branch interfaces it composes and exercises the real journey from entry point to observable result.

When that tracer is contained within one feature branch, ordinary depth-first traversal is sufficient. When the smallest meaningful tracer crosses feature or capability ownership boundaries, the same leaves—including the cross-branch tracer—are selected through the optional Proof Slice Gate.

The PRD writer derives each delivery branch, tracer, entry/result boundary, interface dependency, and provisional contract from confirmed outcomes. It records the mapping in `.wbs/context.md` and connects generated nodes back to stable `REQ-*` IDs through `source_requirements`. A provisional interface becomes evidence-backed when its tracer passes; if the tracer changes the contract, affected consumers and tests are reconciled before the branch is treated as complete.

See [Outcome-Driven WBS Specification](outcome-driven-specification.md) for the audited intake/synthesis boundary and acceptance criteria.

---

## The execution loop

```bash
# Get the next leaf — dependency order is enforced automatically
uv run wbs.py next

# (AI reads the JSON output, loads context.md, implements the leaf)

# For deep trees: get the full parent chain for more context
uv run wbs.py show AUTH-MAGICLINK-API

# Optionally record active work (recommended for multi-agent coordination)
uv run wbs.py start AUTH-MAGICLINK-API

# Mark done — runs node and meta.verify checks, then propagates upward
uv run wbs.py done AUTH-MAGICLINK-API

# Only when done reports awaiting_proof_approval: review, then explicitly approve
uv run wbs.py approve-proof

# Check progress
uv run wbs.py status

# Next iteration
uv run wbs.py next
```

### What `next` returns

`next` returns the first executable leaf in a depth-first left-to-right traversal where all dependencies are met. While an unapproved Proof Slice is active, it considers only that slice's members:

```json
{
  "id": "AUTH-USER-REPO",
  "type": "work_package",
  "title": "User repository",
  "objective": "Persist and retrieve client accounts by email",
  "source_requirements": ["REQ-001"],
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
  "context_file": ".wbs/context.md",
  "execution_strategy": "proof_slice_first"
}
```

The AI should read `context_file` alongside this output before implementing.

### What `done` does

0. Refuses if the node has incomplete children, or if any `verify` command exits non-zero — the node's own `verify` list plus the optional `meta.verify` list (project-wide regression gate: full test suite, lint, typecheck — runs on every `done`)
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

## Proof Slice Gate

Normal depth-first traversal is already vertical when an outcome-bearing feature contains its implementation and tracer leaves. A Proof Slice is only for the narrower case where the first architectural proof crosses delivery-branch ownership boundaries.

### Strategy selection

```bash
# Inspect the effective configuration
uv run wbs.py strategy

# Default: enforce a declared Proof Slice
uv run wbs.py strategy proof_slice_first

# Compatibility: ignore the gate and use unrestricted dependency-aware DFS
uv run wbs.py strategy legacy_bottom_up
```

The setting is persisted as `meta.execution_strategy`. Missing values default to `proof_slice_first`, so existing trees do not require migration. In legacy mode, a `proof_slice` remains visible for provenance but `status` reports it as unenforced. Strategy changes require explicit user direction.

It is a top-level execution overlay, not a node or second hierarchy:

```yaml
proof_slice:
  id: PROOF-FIRST-RUN
  objective: A new user signs in and creates one persisted workspace
  hypothesis: Auth, API, persistence, and UI boundaries compose without redesign
  nodes:
    - AUTH-MINIMUM-FLOW
    - WORKSPACE-CREATE-DATA
    - WORKSPACE-CREATE-API
    - UI-FIRST-RUN
    - FIRST-RUN-E2E
  acceptance_criteria:
    - A browser completes the journey from sign-in to persisted workspace
  verify:
    - pytest tests/e2e/test_first_run.py -q
  status: pending
```

The member list is ordered preference, not a substitute for dependency edges. Every unresolved dependency of a member must also be listed. Do not invent `sequence` dependencies solely to manipulate product priority.

While the proof is `pending`:

1. `next` considers proof members only and includes the proof objective and hypothesis in its output.
2. `start` and `done` reject non-proof nodes.
3. If no member is executable, `next` returns `proof_slice_blocked` with each member's status and unmet dependencies.
4. Completing the final member runs node verification, `meta.verify`, and the proof's end-to-end `verify` before changing YAML state.

If all checks pass, the proof becomes `verified` and `next` returns `awaiting_proof_approval`. Review what the proof demonstrated and what it invalidated. On explicit human approval:

```bash
uv run wbs.py approve-proof
```

The command re-runs the end-to-end proof, records `approved_at`, and restores ordinary depth-first traversal. A failed check leaves the tree unchanged.

If a proof member is re-decomposed, replace its ID in `proof_slice.nodes` with the new dependency-closed leaf IDs before running `validate`.

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

A decomposed node is not complete — it's a parent waiting for its children. The original node's `status` becomes `decomposed`; `wbs.py` does not copy its acceptance criteria, so the editor must distribute or refine them on the new children before validating.

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

Runs the node's `verify` commands and the optional project-wide `meta.verify` commands, then marks a node complete and propagates upward. It refuses incomplete dependencies or children, failed verification, and nodes outside an active Proof Slice.

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

### `strategy [name]`

Shows the effective execution strategy when called without an argument. Passing a name persists the project configuration in `meta.execution_strategy`.

```bash
uv run wbs.py strategy
uv run wbs.py strategy proof_slice_first
uv run wbs.py strategy legacy_bottom_up
```

### `approve-proof`

Re-runs a verified Proof Slice's end-to-end commands, records approval, and unlocks ordinary traversal. It refuses pending proofs and must only be called after explicit human approval.

```bash
uv run wbs.py approve-proof
```

### `status`

Progress dashboard.

```bash
uv run wbs.py status
# {
#   "project": "client-portal",
#   "execution_strategy": "proof_slice_first",
#   "total_nodes": 12,
#   "complete": 4,
#   "completion_pct": 33,
#   "by_status": {"complete": 4, "pending": 7, "in_progress": 1},
#   "next": "AUTH-MAGICLINK-VERIFY",
#   "scheduler_status": "ready",
#   "proof_slice": null
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

Scaffolds a skeleton `tree.yaml` and `context.md` from an existing PRD file, and copies the toolkit's bundled schema to `node-template.yaml`. The skeleton sets `meta.execution_strategy: proof_slice_first` and adds the outcome-ledger sections, but is intentionally incomplete. The `wbs-prd` skill is the preferred way to generate the tree from scratch via conversation.

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
| `meta.execution_strategy` is `proof_slice_first` or `legacy_bottom_up` when present | Whole tree |
| `source_requirements`, when present, is a list of non-empty requirement IDs | All nodes |
| No duplicate node IDs | Whole tree |
| All `dependencies[].id` values resolve to existing nodes | All nodes |
| `dependencies[].type` is one of: `data`, `sequence`, `runtime` | All nodes |
| `acceptance_criteria` list is non-empty | Leaf nodes (not `decomposed`) |
| `acceptance_criteria` and verification entries contain only non-empty strings | Wherever present |
| Every executable leaf has commands in its own `verify` or project-wide `meta.verify` | Leaf nodes (not `decomposed`) |
| No dependency cycles (including a node depending on its own ancestor) | Whole tree |
| Proof Slice fields, status, and commands are present and valid | Optional `proof_slice` |
| Proof members exist, are unique leaves, and include every unresolved dependency | Optional `proof_slice` |
| A `verified` or `approved` proof has no incomplete members | Optional `proof_slice` |

All read and state-management commands except `init` and `validate` refuse an invalid tree. Fix validation errors before executing.

### Trust and concurrency boundary

Verification entries run as shell commands in the directory where `wbs.py` is invoked. Treat `.wbs/tree.yaml` as executable project configuration: review commands supplied by generators, collaborators, or external sources before running `done` or `approve-proof`, and invoke the CLI from the project root.

Tree replacement is atomic, so interruption cannot leave a partially written YAML document. It is still a single-writer state store: parallel implementation is safe only when one controller serializes all WBS state-changing commands. `start` records coordination state; it is not a distributed lease or lock.

---

## context.md — the executor's briefing file

`.wbs/context.md` is the project-level context file the AI loads alongside every leaf node. It begins with the confirmed outcome ledger, then records the PRD writer's derived delivery mapping and implementation context.

```markdown
# Project Context

## Outcome Requirements
| ID | Actor | Trigger | Observable result | Evidence | Failure behavior | Priority | Constraints / assumptions |
|---|---|---|---|---|---|---|---|
| REQ-001 | Client | Requests a magic link | Receives an authenticated session | End-to-end browser test | Invalid and expired links are rejected | Required now | Complete within 60 seconds |

## Tech Stack
- Python 3.12, FastAPI, Pydantic v2
- PostgreSQL 16 (primary store), Redis 7 (cache + token TTLs)
- React 18 + TypeScript, Vite, Tailwind CSS

## Conventions
- API: RESTful, /api/v1/, snake_case JSON
- Tests: pytest + httpx; no DB mocks — use test database
- Errors: RFC 9457 Problem Details format

## Delivery Branches
- AUTH-MAGICLINK → REQ-001
- Tracer: AUTH-MAGICLINK-E2E
- Entry → result: POST /auth/magic-link → authenticated session
- Interfaces are provisional until the tracer passes; known consumers are listed here

## Architecture Notes
- Monorepo: backend/, frontend/, infra/
- Multi-tenant: every query scoped by tenant_id from JWT claims

## Non-Functional Requirements
- p95 response time < 200ms under 500 concurrent users
- SOC 2 Type II: PII encrypted at rest, audit log for auth events
```

Keep it dense and factual. The outcome ledger contains confirmed user requirements; delivery branches and architecture sections are the PRD writer's derived representation. Do not rewrite technical assumptions as if the user supplied them. The AI reads this file cold before implementing each leaf.

---

## Tips for AI agents

When using `wbs.py` as part of an agentic loop:

**Always read `context_file` before implementing.** The leaf node JSON includes a `context_file` path. Load it. It has the tech stack and conventions that determine how to implement the node correctly.

**Use `show <id>` for full ancestry.** `next` returns only the immediate parent's intent. For nodes deep in the tree, `show` gives you the full chain from ROOT to leaf — useful for understanding *why* a node exists.

**Treat a Proof Slice as an evidence gate.** Work only its returned leaves, report `proof_slice_blocked` rather than escaping to unrelated work, and never call `approve-proof` without explicit user approval.

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

---
name: wbs-prd
description: Use this skill when starting a new project, feature, or module — before any code is written. Relentlessly interviews the user to extract scope, capabilities, features, dependencies, and acceptance criteria, then synthesizes the results into a WBS-compatible .wbs/tree.yaml and .wbs/context.md ready for wbs.py to execute. Triggers on: "spec this out", "plan this", "I want to build", "grill me on this", "PRD this", "generate the WBS", "create the tree", "scaffold the tree", "let's plan before we build", or any request to capture requirements before coding.
---

## Gotchas

- Do NOT write `tree.yaml` until grilling is complete. Synthesis is pure transformation — don't blend extraction and writing.
- Decompose to **work_package** level only. Task and step nodes are for execution time via `wbs.py decompose`. Over-specifying upfront wastes effort on decisions that change.
- Every leaf node needs at least one `acceptance_criteria` item. Vague or missing criteria make "done" undefined — `wbs.py validate` will reject leaves without them.
- Dependencies must reference node IDs that exist elsewhere in the same tree. Resolve the order of nodes before writing.
- Tech stack and conventions belong in `.wbs/context.md`, not in node `constraints`. Node constraints are functional (what the node must/must not do), not environmental.
- If `.wbs/tree.yaml` already exists, read it and ask whether to overwrite or append new capabilities. Never silently overwrite. When revising, first ask: "What did we learn since the last version that changes the *problem*, not just the plan?" Log the answer in context.md — partial builds reveal problem dimensions the original grilling couldn't see.
- `--tree` is a global flag in `wbs.py` — it goes **before** the subcommand: `wbs.py --tree path/tree.yaml validate`, not `wbs.py validate --tree path/tree.yaml`.
- For deep trees, run `wbs.py show <id>` after `next` to get the full parent chain — `next` only returns the immediate parent's intent.
- Run `wbs.py validate` before reporting success. A tree the validator rejects is not done.

---

## Phase 1: Grilling

Interview me relentlessly about every aspect of this product or feature until you have enough to populate every field in the WBS tree without uncertainty. Walk down the hierarchy in order — scope, then capabilities, then features, then work packages. Resolve dependencies between decisions one by one.

**Ask one question at a time.** Wait for the answer. Asking multiple questions at once is bewildering.

**For each question, give your recommended answer.** The user reacts to a concrete proposal rather than generating from scratch. This surfaces disagreement faster and moves sessions forward.

**If a question can be answered by exploring the codebase, explore the codebase instead of asking.**

### Question sequence

**Scope** → becomes the ROOT node
- What is the single-sentence objective? What problem does this solve and for whom?
- Who are the user types (actors who appear in acceptance criteria)?
- What is the unifying mental model — the one coherent story this design tells? Every capability must map to it; this becomes `## Core Design Concepts` in context.md and the integrity check at synthesis.
- What existing system is this most like, and where does it deliberately differ? A good exemplar imports a proven decomposition for free.
- What is the second-most-viable overall approach, and why isn't it the one? Record the rejected path and one-line rationale — it goes in `## Design Alternatives` in context.md.
- What is explicitly out of scope? Name it — it becomes root-level constraints.
- What does "done" look like at the top level?

**Capabilities** → become `CAP-{DOMAIN}` nodes
- What are the 3–7 major capability domains? Each should be independently deliverable and map to a core design concept — a capability that maps to none is scope creep or a sign the mental model is wrong.
- For each: what does "done" look like? What acceptance criteria prove it's complete?
- For each: was there a materially different way to slice or build this? If yes, one line on why not — into `## Design Alternatives`.

**Features** → become `{DOMAIN}-{FEATURE}` nodes, one capability at a time
- What features make up this capability?
- Which features must complete before others can start? (dependency type: `sequence`)
- Which features need data or output produced by another feature? (dependency type: `data`)
- Which features must be deployed together to function? (dependency type: `runtime`)
- Acceptance criteria for each feature — including edge cases that would catch a broken implementation.

**Work packages** → become `{DOMAIN}-{FEATURE}-{UNIT}` nodes, one feature at a time
- What discrete deliverables make up this feature? (API endpoints, data models, UI components, test suites, migrations — each is typically a work package)
- Draw boundaries for deep modules: a work package's `outputs` list is its interface. Prefer fewer packages with narrow outputs that hide real functionality; outputs that enumerate internals mean the boundary is drawn wrong — merge or redraw.
- What inputs does each work package need before it can start?
- What constraints apply to each work package?

**Implementation context** → becomes `.wbs/context.md`
- Tech stack (languages, frameworks, databases, infra)?
- Definition of Done: what commands must pass before any node is marked complete (test suite, lint, typecheck)? These become `meta.verify` in tree.yaml — run automatically on every `wbs.py done`.
- Hard non-functional constraints: performance targets, security requirements, compliance obligations?
- External integrations and their contracts?
- Existing conventions or patterns to follow?

**Stop when** you can fill every field in the schema for every node down to work_package level without uncertainty. If any field would be left blank or vague, ask one more targeted question.

**Contracting point** — before synthesis, present a short summary: what's decided, what's assumed, what's still open. Get an explicit yes. Open questions are not silently resolved by your own recommendations — they go into `## Open Questions` in context.md.

---

## Phase 2: Synthesis

Read `references/node-schema.md` now — it has the full field reference, valid values, and a complete tree.yaml example. Use it throughout synthesis.

Do NOT re-interview. Synthesize only from what was established in the grilling session.

1. Check whether `.wbs/tree.yaml` exists. If yes, read it and confirm with the user before proceeding.
2. Create `.wbs/` directory if it doesn't exist: `mkdir -p .wbs`.
3. Write `.wbs/tree.yaml` with the complete tree from the grilling session. Include the full `meta` section: `project`, `version: "0.1.0"`, `prd_source: "conversation"`, `tech_stack` (from grilling), `conventions: "See .wbs/context.md"`, `verify` (the Definition-of-Done commands — `wbs.py done` runs them on every completion). Set all node statuses to `pending`. Give every leaf a `verify` entry: one command that runs that node's tests (path per the test-file convention in context.md). The test file won't exist yet — that's the point: `done` refuses until the executor writes tests that pass.
4. Write `.wbs/context.md` with: tech stack, conventions, core design concepts, design alternatives, architecture notes, integration points, non-functional requirements, open questions. Follow the format in `references/node-schema.md`. This is the file the AI executor loads alongside every leaf node — the alternatives section stops the executor re-litigating settled decisions or implementing a pruned path.
5. Integrity check: walk the tree and confirm every capability and feature maps to a core design concept, and every work package's outputs read as a narrow interface, not a list of internals. A node that maps to nothing gets cut, merged, or triggers one more grilling question — don't paper over it.
6. Run `wbs.py validate`. Fix any errors before continuing.
7. Run `wbs.py status` and show the user the result — total nodes, structure, and what's next.

### Node ID convention

| Level | Pattern | Example |
|---|---|---|
| product | `ROOT` | `ROOT` |
| capability | `CAP-{DOMAIN}` | `CAP-AUTH` |
| feature | `{DOMAIN}-{FEATURE}` | `AUTH-MAGICLINK` |
| module | `{DOMAIN}-{FEATURE}-{MODULE}` | `AUTH-MAGICLINK-TOKENS` |
| work_package | `{DOMAIN}-{FEATURE}-{UNIT}` | `AUTH-MAGICLINK-API` |

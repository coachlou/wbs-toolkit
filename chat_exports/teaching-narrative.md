# Teaching Narrative: Recursive Development — From Concept to AI-Native Dev System

**Session date:** 2026-06-30
**Raw material for:** AIMM teaching block / educational article
**Audience:** Knowledge entrepreneurs — coaches, consultants, course creators, expert practitioners building digital products and services

---

## 1. The Initial Idea — The Spark

Lou came into this session with a concept, not a problem. The question wasn't "how do I fix this?" — it was "what if software development worked like this?"

The insight: **software development can be conceived as a recursive implementation of a Work Breakdown Structure (WBS).**

In project management, a WBS is a hierarchical decomposition of a project into smaller, manageable components. Lou's idea was to apply this to the actual *coding* process — not as a planning artifact but as the operating system for development itself.

The model:
- A PRD (Product Requirements Document) deconstructs an app into atomic units arranged in a tree hierarchy
- Product → Capabilities → Features → Modules → Work Packages → Tasks → Steps
- The development process becomes a depth-first walk of that tree, implementing from the bottom up

The key word is **recursive**. Every node in the tree — whether it describes an entire SaaS product or a single API endpoint validation function — uses the *same schema*, answers the *same questions*, and is processed by the *same algorithm*. The same loop that builds a function builds a feature builds a product.

**Why this matters for knowledge entrepreneurs:** Most people think of software development as a specialist activity — something you hire developers for. But this framing reveals it as something more fundamental: a *knowledge decomposition process*. And knowledge decomposition is something knowledge entrepreneurs do all day — in courses, frameworks, consulting methodologies, and systems. This conversation started with code but ended somewhere much bigger.

---

## 2. The Journey — What, Why, How

### Phase 1: Concept Validation (The Tree vs. The Graph)

Lou presented the core model. The immediate conversation was about what holds and what doesn't.

**What held:**
- The self-similarity is real. The same decompose → implement → compose loop applies at every scale. You're not switching between "architecture mode" and "coding mode" — it's the same move, recursively applied.
- Depth-first bottom-up implementation solves the dependency ordering problem automatically. If you've decomposed correctly, a leaf node has no incomplete dependencies by definition.
- Progress becomes objective. Percentage of leaf nodes implemented = percentage complete. No more "60% done" ambiguity.
- The spec and the work become the same artifact. Most PRDs describe the system in one language; implementation expresses it in another, with translation losses at every handoff. If the spec IS the decomposition tree, that gap closes.

**The challenge raised — and resolved:**
Real systems are graphs (nodes with multiple parents), not pure trees. Auth, logging, shared data models — these appear in multiple places.

Lou's resolution: a graph of trees. Cross-cutting concerns (auth, a shared user model, a mail service) become their own WBS trees. Other trees that depend on them carry explicit dependency edges. The recursive property is preserved everywhere — every node in every tree is still decomposable by the same algorithm.

This actually makes the model *stronger*, not weaker. In a flat graph, a shared node has no internal structure. In Lou's forest model, a shared concern is a *fully specified subtree* with its own decomposition, its own leaves, its own implementation order — and typed dependency edges to other trees (data dependency vs. sequencing constraint vs. runtime dependency).

### Phase 2: Schema Design — The Self-Similar Node

Lou brought a developed schema. Every node, at every level, carries the same fields:
- **id** — unique hierarchical identifier
- **type** — where in the hierarchy this node lives
- **title** — short imperative phrase
- **objective** — one sentence: what this delivers and why
- **inputs** — what the node needs to start
- **constraints** — what it must conform to
- **outputs** — concrete deliverables
- **acceptance_criteria** — verifiable conditions that prove it's done
- **dependencies** — what must complete before this can execute
- **owner** / **agent_type** — who or what executes this
- **children** — sub-nodes, same schema (empty = leaf)

The three questions that drive the recursion: *What must be delivered? What child units fully cover this scope? Is this node executable yet?*

The operating loop: ingest brief → decompose → expand to executable leaves → route to builders → verify against acceptance criteria → propagate results upward → replan where blocked. If a leaf fails or turns out to be too large, it becomes a new parent and gets decomposed again. That's where the system becomes genuinely recursive rather than a static task tree.

### Phase 3: Building the Tool — wbs.py

The design constraint Lou set: **run from within Claude Code or Codex — AI-coder friendly.**

This collapsed the architecture significantly. Claude Code (or any AI coder) IS the planner and executor. The tool doesn't need to manage agents — it just needs to manage tree state and tell the AI what to work on next.

Form factor: a single Python CLI file (`wbs.py`) operating on a YAML tree stored on disk.

Key commands:
- `wbs.py next` — returns the next executable leaf as JSON (respecting dependency ordering)
- `wbs.py done <id>` — marks a node complete and propagates completion upward automatically
- `wbs.py decompose <id>` — marks a node for re-expansion (AI then edits the tree directly)
- `wbs.py validate` — schema and integrity check (catches bad dependencies, missing acceptance criteria, invalid types)
- `wbs.py status` — progress dashboard

The AI agent runs a simple loop: get next leaf → read node + parent intent + project context → implement → mark done → repeat.

Dependency ordering is enforced automatically. If work package B depends on work package A, `wbs.py next` will never return B until A is complete. Status propagates upward: when all children of a parent are complete, the parent auto-completes. When all capabilities are done, the product is done.

### Phase 4: The PRD Skill — Requirements Extraction

The PRD skill is the upstream input to the whole system. Before you can execute the tree, you have to build it. And building it means extracting requirements from a human — which requires a structured interview.

Research: Lou pointed to Matt Pocock's "grilling" skills on GitHub. These are minimal, powerful Claude skills that interview relentlessly, one question at a time, always giving a recommended answer for the user to react to rather than asking open questions.

Pocock's core engine is four sentences. The leading word — "relentlessly" — anchors an entire region of behavior. The constraints: one question at a time, give your recommended answer, explore the codebase instead of asking if you can answer it yourself.

The `wbs-prd` skill adapts this pattern with WBS-awareness:
- Phase 1: Grilling — questions specifically targeting the decomposition hierarchy (scope → capabilities → features → work packages) and hunting for dependencies, acceptance criteria, and the context that belongs in `context.md`
- Phase 2: Synthesis — pure transformation of the conversation into `tree.yaml` + `context.md`, no re-interviewing

After the interview, the AI writes the files directly. The YAML tree is ready to execute against `wbs.py next`.

### Phase 5: Audit — Fixing What Was Wrong

A rigorous audit of the skill and tool found 11 issues — ranging from a broken command invocation (`wbs.py init` was being called with the wrong argument type) to missing validation (the validator didn't enforce that leaf nodes need acceptance_criteria, contradicting the skill's own rule), to inconsistent example IDs between files.

Every issue was fixed. The audit process itself is instructive: this is what it looks like to build a system rather than a script. The skill, the tool, the schema, and the library entry all need to be internally consistent. When they're not, agents trained on them produce subtly wrong output that's hard to diagnose.

---

## 3. The Ultimate Result

At the end of this session, a complete recursive development system exists:

**`wbs.py`** — a 390-line Python CLI that manages WBS tree state. Self-contained, runs with `uv run wbs.py`. No server, no database, no dependencies beyond PyYAML. The tree lives as a human-readable YAML file on disk. All output is JSON for AI consumption.

**`wbs-prd` skill** — a Claude Code skill that interviews the user to extract requirements, then synthesizes the conversation into `tree.yaml` + `context.md`. Installed at `~/.claude/skills/wbs-prd/` and in the canonical skill library at `$AMBIENT_LIBRARY_ROOT/skills/wbs-prd/`.

**The schema** — a self-similar node format documented in `.wbs/node-template.yaml` (project-level reference) and `skills/wbs-prd/references/node-schema.md` (skill-level reference). Every node at every level uses the same fields. The PRD skill generates against this schema; `wbs.py validate` enforces it.

**The loop:**
```
/wbs-prd                     ← interview + generate tree.yaml + context.md
uv run wbs.py next           ← get next executable leaf (JSON, deps respected)
[AI implements the leaf]     ← reads node + parent intent + context.md
uv run wbs.py done <id>      ← marks complete, propagates upward
uv run wbs.py next           ← repeat
```

If a leaf is too large: `wbs.py decompose <id>` → AI edits `tree.yaml` to add children → `wbs.py validate` → same loop restarts on the children.

---

## 4. Use Case, Application, and Benefit to Knowledge Entrepreneurs

### The obvious application: building digital products

For knowledge entrepreneurs who are building software — a membership platform, a course delivery system, a coaching app, an AI-powered assessment tool — this system makes the project tractable.

The biggest problem with "I want to build an app" isn't the building. It's that the scope is undefined, the dependencies are invisible, the acceptance criteria are vague, and progress is unmeasurable until the last 10% of the work. This system solves all four:
- Scope is defined by the decomposition (what's in the tree)
- Dependencies are explicit (typed edges between nodes)
- Acceptance criteria are required for every leaf before the AI will execute
- Progress is a number: X of Y leaf nodes complete

And because the AI agent (Claude Code or Codex) IS the executor — not a hired developer — the feedback loop is tight. You `/wbs-prd` your idea, review the tree, and start executing within an hour.

### The deeper application: any complex knowledge product

Here's the insight that generalizes: **the WBS paradigm isn't specific to code.**

A course can be decomposed the same way:
- Product: "Complete Video Editing Course"
- Capabilities: Foundations, Storytelling, Technical Mastery, Business
- Features: each module within a capability
- Work packages: individual lessons, exercises, downloads, assessments
- Leaf nodes: individual pieces of content the AI can draft

A consulting methodology can be decomposed:
- Product: "90-Day Business Transformation Program"
- Capabilities: Assessment, Strategy, Implementation, Accountability
- Features: each phase and its components
- Work packages: frameworks, worksheets, client-facing documents

A newsletter can be decomposed. A mastermind curriculum can be decomposed. A coaching package can be decomposed.

In every case, the same three questions apply: *What must be delivered? What child units cover this scope? Is this node executable?* And in every case, the same principle holds: **the parent defines intent, the children define composition, the leaves define execution.**

### The meta-lesson: AI amplifies structured thinking

The reason this system works with AI is that AI is exceptionally good at executing well-specified, bounded tasks — and exceptionally poor at figuring out what the task is in the first place.

The WBS model solves the second problem at design time. Once the tree exists, every leaf is a fully specified, bounded task: objective, inputs, constraints, outputs, acceptance criteria, dependencies, parent intent, and project context. The AI has everything it needs and nothing it doesn't.

Without this structure, AI coding sessions sprawl. The AI doesn't know when to stop, what "done" looks like, or what the next thing is. With the tree, every session is atomic and complete. The loop is clean.

For knowledge entrepreneurs building their AI-assisted business: the competitive advantage isn't access to AI tools — everyone has that. It's the quality of your *decomposition*. People who can break complex things into well-specified parts will extract dramatically more value from AI than people who bring vague instructions to a capable model. That's what this system is training.

---

## Key Quotes / Pull Lines for the Article

- "The recursion stops when a node is small enough to execute — meaning it can be built, tested, and verified independently in a single AI agent session."
- "The parent defines intent. The children define composition. The leaves define execution."
- "Progress is a number: X of Y leaf nodes complete. No more '60% done' ambiguity."
- "The competitive advantage isn't access to AI tools — it's the quality of your decomposition."
- "A course can be decomposed the same way. A consulting methodology can be decomposed. A newsletter, a mastermind curriculum, a coaching package — all of it."
- "AI is exceptionally good at executing well-specified, bounded tasks — and exceptionally poor at figuring out what the task is. The WBS model solves the second problem at design time."
- "The spec and the implementation become the same artifact. Most PRDs describe the system in one language; implementation expresses it in another, with translation losses at every handoff. This closes the gap."

---

## Suggested Article Structure

1. **Hook:** The problem with "I want to build an app" — scope is undefined, progress is invisible
2. **The insight:** Software development as recursive WBS — one algorithm, all scales
3. **The schema:** Show the self-similar node (just the key fields, not all of them)
4. **The loop:** The 4-step AI execution cycle
5. **The generalization:** This works for courses, methodologies, content systems too
6. **The meta-lesson:** Decomposition quality is the new leverage
7. **Call to action:** Start with a single project. Ask the three questions.

---

*Raw material compiled from session on 2026-06-30. See `2026-06-30-conversation-export.md` for full conversation transcript.*

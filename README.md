# recursive-development

A recursive Work Breakdown Structure (WBS) system for AI-driven software development.

Every node in the tree — from the top-level product down to a single work package — uses the same self-similar schema. Leaves execute in dependency-aware, depth-first order. In the default `proof_slice_first` strategy, a declared cross-branch Proof Slice is verified and explicitly approved before ordinary traversal resumes; without one, execution follows the same normal traversal. Each leaf can be executed by Claude Code, Codex, or another AI coder.

---

## Core idea

A PRD writer first captures functionality and observable evidence in the user's language, then compiles those requirements into a tree of work. It—not the user—derives branches, leaves, dependencies, tracers, and any Proof Slice. Each node answers three questions:

1. **What must be delivered?**
2. **What child units fully cover this scope?**
3. **Is this node executable yet?**

The recursion stops when a node is small enough for a single AI agent session. The AI reads the leaf, implements it, marks it done. Completion propagates upward automatically.

---

## Installation

Keep the extracted toolkit directory intact: `wbs.py` uses its bundled `.wbs/node-template.yaml` when initializing another project.

**Skills:** Copy `skills/wbs-prd/` and `skills/wbs-exec/` to `~/.claude/skills/`, or symlink:

```bash
ln -s /path/to/recursive-development/skills/wbs-prd ~/.claude/skills/
ln -s /path/to/recursive-development/skills/wbs-exec ~/.claude/skills/
```

**Per project:** either copy `wbs.py` and `.wbs/node-template.yaml` into the target project, or invoke the toolkit copy from the target project root:

```bash
cd /path/to/your-project
uv run /path/to/recursive-development/wbs.py init docs/prd.md
```

`init` creates `.wbs/tree.yaml`, `.wbs/context.md`, and copies the bundled schema to `.wbs/node-template.yaml`. If the PRD skill creates the tree directly, keep `wbs.py` available at the project root or provide its explicit toolkit path.

### Ambient-folder installation

The repository also ships a portable `distro/` source package for the
`.aai`/`.ailib` model. After it is synced to the ambient library as
`wbs-toolkit`, install it into a project with the ambient-folder installer:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/library/ambient-folder/install.sh" \
  wbs-toolkit --check /path/to/project
bash "${CLAUDE_PLUGIN_ROOT}/library/ambient-folder/install.sh" \
  wbs-toolkit /path/to/project
```

That stamps an owned `.aai/` behavior profile once, vendors a pinned
`.ailib/wbs-toolkit/` runtime and skills, and creates `wbs.sh` at the project
root. Run `bash wbs.sh next` (or any other WBS command) from the installed
project. Re-running the installer refreshes `.ailib/` without touching the
project’s `.aai/` profile or `.wbs/` execution state.

## Quick start

**Requires:** Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) (or `pip install pyyaml`)

```bash
# 1. Spec a project via the wbs-prd Claude Code skill
/wbs-prd          # interviews you, writes .wbs/tree.yaml + .wbs/context.md

# 2. Inspect the effective strategy (proof_slice_first is the default)
uv run wbs.py strategy

# Optional compatibility mode: persist legacy unrestricted DFS
uv run wbs.py strategy legacy_bottom_up

# 3. Get the next executable leaf
uv run wbs.py next

# 4. Implement the leaf (AI reads the JSON output and acts)
uv run wbs.py start <node-id> # optional, records in_progress

# 5. Mark it done — runs the node's verify commands + tree.yaml's meta.verify
#    (project-wide gate: full test suite, lint, typecheck), then propagates upward
uv run wbs.py done <node-id>

# Only if done returns awaiting_proof_approval: review evidence, then explicitly approve
uv run wbs.py approve-proof

# 6. Repeat — after approval, or immediately for ordinary trees
uv run wbs.py next
```

`approve-proof` applies only when `.wbs/tree.yaml` contains an optional `proof_slice` and `done` reports `awaiting_proof_approval`. Do not run it for ordinary trees.

If a leaf is too large for one session:
```bash
uv run wbs.py decompose <node-id>
# Edit .wbs/tree.yaml to add children under that node and distribute/refine its criteria
uv run wbs.py validate
uv run wbs.py next   # now returns one of the children
```

---

## Commands

`--tree PATH` is a global flag that goes **before** the subcommand (default: `.wbs/tree.yaml`).

| Command | Description |
|---|---|
| `wbs.py next` | Next executable leaf as JSON — respects dependencies and an active Proof Slice |
| `wbs.py show <id>` | Full node + parent chain as JSON — load into agent context |
| `wbs.py done <id>` | Run node and project verification, then mark complete and propagate status |
| `wbs.py start <id>` | Mark `in_progress` |
| `wbs.py block <id> [--reason "..."]` | Mark `blocked` |
| `wbs.py decompose <id>` | Mark for re-expansion; edit tree, then validate |
| `wbs.py strategy [name]` | Show or persist `proof_slice_first` / `legacy_bottom_up` |
| `wbs.py approve-proof` | Re-verify and approve a verified Proof Slice, unlocking ordinary traversal |
| `wbs.py status` | Progress dashboard, including strategy and Proof Slice gate state |
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

A work-package leaf is the agent execution unit; an outcome-bearing feature branch is the delivery unit. Build that branch bottom-up internally, then close it with an explicit `*-E2E` tracer leaf that exercises its real entry-to-result journey. If the required tracer crosses feature or capability branches, use the Proof Slice Gate to select its dependency-closed leaves before broader work.

## Proof Slice Gate

An outcome-bearing feature branch that contains its implementation leaves and tracer executes vertically under normal depth-first traversal. Use `proof_slice` only when the smallest architectural proof crosses delivery-branch ownership boundaries.

`proof_slice_first` is the default execution strategy for new and existing trees. It enforces a declared Proof Slice; if none exists, normal branch traversal continues. Select the compatibility behavior with `wbs.py strategy legacy_bottom_up`; that mode keeps the Proof Slice as provenance but does not enforce its gate.

The optional top-level object references a dependency-closed set of existing leaves. While it is `pending`, only those leaves can start or complete. Finishing the last member runs the proof's end-to-end verification and pauses at `verified`; explicit `approve-proof` rechecks the evidence and unlocks the rest of the WBS. The proof does not change node parentage or misuse dependencies as product-priority signals.

---

## The wbs-prd skill

Install location: `~/.claude/skills/wbs-prd/`

Trigger in Claude Code with any of: `"spec this out"`, `"plan this"`, `"I want to build"`, `"grill me on this"`, `"PRD this"`, `"generate the WBS"`, `"create the tree"`.

The skill interviews you about actors, behavior, observable results, evidence, failure cases, priorities, and constraints—one question at a time with a recommended answer. It then derives the technical WBS and writes `.wbs/tree.yaml` plus `.wbs/context.md` ready for execution. See the [Outcome-Driven WBS Specification](docs/outcome-driven-specification.md).

---

## Output contract

Successful `wbs.py` commands emit JSON to stdout. Operational errors go to stderr with a non-zero exit code; `validate` emits its JSON validation report to stdout and exits non-zero when invalid. This makes every result scriptable and AI-readable.

### Trust and concurrency boundary

`verify` entries are shell commands. Run WBS trees only from trusted projects, and review generated or externally supplied verification commands before calling `done` or `approve-proof`.

The tree file has atomic replacement protection but is a single-writer state store. Parallel agents may implement independent leaves, but one controller must serialize `start`, `block`, `decompose`, `strategy`, `done`, and `approve-proof` mutations.

Example `next` output:
```json
{
  "id": "AUTH-MAGICLINK-API",
  "type": "work_package",
  "title": "Magic-link request endpoint",
  "objective": "Accept an email and issue a short-lived signed login token",
  "source_requirements": ["REQ-001"],
  "inputs": ["User model (AUTH-USER-REPO)"],
  "constraints": ["Stateless API", "Token expiry: 15 minutes"],
  "outputs": ["POST /auth/magic-link", "Token stored in Redis"],
  "acceptance_criteria": ["Invalid email → 422", "Valid request → 200"],
  "dependencies": [{"id": "AUTH-USER-REPO", "type": "data"}],
  "parent_intent": "Secure, passwordless client login with no IT support burden",
  "depth": 2,
  "context_file": ".wbs/context.md",
  "execution_strategy": "proof_slice_first"
}
```

# {{NAME}} — WBS behavior

## When this applies

Use this behavior when the user asks to define, revise, execute, inspect, or
recover a software-development work plan in this project: “spec this out,”
“grill me on this,” “generate the WBS,” “what should we build next,” “run the
next work package,” “show progress,” or “why is this blocked.”

## Inputs

| File | Kind | Load when |
|---|---|---|
| `~/.aai/identity.md`, `purpose.md`, `context.md`, `memory.md` | reference | Always if the owner has a global ambient home; then load its core rules. |
| `.wbs/context.md` | working | Before implementing or reviewing any WBS leaf. |
| `.wbs/tree.yaml` | working state | Before scheduling, changing status, or explaining progress. |
| `.ailib/wbs-toolkit/app/skills/wbs-prd/` | vendored capability | Before requirements intake or WBS synthesis; resolve `.aai/skills/wbs-toolkit/` first if it provides a customized equivalent. |
| `.ailib/wbs-toolkit/app/skills/wbs-exec/` | vendored capability | Before agent-led execution of a returned leaf. |
| `.ailib/wbs-toolkit/app/docs/user-guide.md` | reference | Before diagnosing schema, traversal, or Proof Slice behavior. |

## Process

1. **Specify:** Run the PRD workflow in user language. Confirm an
   outcome-requirement ledger—actor, trigger, observable success, evidence,
   failure behavior, priority, constraints, exclusions, and assumptions—before
   deriving WBS structure. Create `.wbs/tree.yaml` and `.wbs/context.md`.
2. **Validate:** Run `bash wbs.sh validate` after any manual WBS edit. Inspect
   `bash wbs.sh strategy` before scheduling; the default is
   `proof_slice_first`.
3. **Execute:** Run `bash wbs.sh next`; load its JSON and `.wbs/context.md`.
   Implement and review only that packet, then use `start` and `done`. `done`
   runs the leaf and project-level verification commands before advancing state.
4. **Prove:** When a cross-branch Proof Slice reaches `verified`, present what
   the proof demonstrated and what it invalidated. Run `approve-proof` only on
   explicit owner approval. Do not substitute a fake dependency for product
   priority.
5. **Recover:** For a blocked or oversized leaf, record a factual reason or
   decompose it, validate the amended tree, and resume from `next`. Do not mark
   partially implemented work as complete.
6. **Update:** Re-run the ambient-folder installer to refresh `.ailib/`.
   It must leave this `.aai/` profile and `.wbs/` state untouched.

## Outputs

- `.wbs/tree.yaml` — outcome traceability, execution plan, and live status.
- `.wbs/context.md` — project context agents load with each leaf.
- `.wbs/node-template.yaml` — local schema reference copied by `init`.
- Code and review evidence in the project’s normal source and test locations.

## Rules

- Run only trusted `verify` commands; WBS verification can execute shell code.
- Preserve the difference between test evidence, code-review findings, and an
  owner’s Proof Slice approval.
- Do not create an application UI or service merely to operate this CLI.
- `legacy_bottom_up` is a compatibility mode, selected only by explicit user
  direction; it does not enforce a declared Proof Slice gate.

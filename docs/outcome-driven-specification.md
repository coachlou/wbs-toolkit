# Outcome-Driven WBS Specification

**Status:** Final implementation-driving specification
**Applies to:** `wbs-prd`, WBS node generation, branch tracers, and Proof Slice selection

## Decision

The requirements interview is based on functionality and observable results. It does not ask the user to design the WBS.

The PRD writer acts as a compiler:

```text
user purpose and requirements
→ outcome-requirement ledger
→ internal delivery branches and technical leaves
→ branch tracer evidence
→ optional cross-branch Proof Slice
```

Bottom-up construction and vertical validation are complementary. A coherent delivery branch may be built bottom-up internally, then validated through an ordinary `*-E2E` tracer leaf. A Proof Slice is needed only when the first meaningful proof crosses delivery-branch ownership boundaries.

## Audited corrections

The earlier refinement correctly distinguished execution, delivery, and proof units, but put internal design questions into the interview. That violated the abstraction boundary and risked making users reverse-engineer the implementation model.

The corrected design establishes two contracts:

1. **Outcome intake:** capture actors, triggers, observable results, evidence, failure behavior, priorities, constraints, and open assumptions.
2. **Technical synthesis:** derive capabilities, delivery branches, leaves, dependencies, tracers, provisional interfaces, and Proof Slice membership from the confirmed outcomes and repository evidence.

Technical uncertainty is not automatically a user question. Inspect the repository first. Ask only when a choice materially changes behavior, risk, cost, or scope, and phrase the question in those terms.

## Required outputs

### Outcome-requirement ledger

`.wbs/context.md` contains stable `REQ-###` entries with:

- actor;
- trigger;
- observable result;
- acceptance evidence;
- material failure behavior;
- priority;
- constraints and open assumptions.

### Traceable WBS

Every newly generated WBS node has `source_requirements`. Every required-now outcome maps to at least one implementation leaf and one evidence-producing tracer. A structural node may have no direct requirement only when `notes` identifies the delivery branches it enables.

### Delivery branch tracer

Each outcome-bearing branch has one primary `*-E2E` tracer leaf. Its test runs from the declared trigger through real composed interfaces to the observable result. Its dependencies are genuine prerequisites, not priority signals.

### Proof selection

- One branch tracer supplies the first proof: use ordinary depth-first traversal.
- The proof crosses delivery branches: add one minimum dependency-closed `proof_slice` containing the cross-branch tracer.
- Verification supplies evidence; explicit human approval authorizes broader execution.

### Execution strategy configuration

New specifications set `meta.execution_strategy: proof_slice_first`. Existing trees without the field resolve to the same default. When a Proof Slice exists, this configuration enforces it; without one, it retains ordinary dependency-aware branch traversal.

`legacy_bottom_up` is the selectable compatibility configuration. It ignores the Proof Slice gate and uses unrestricted dependency-aware depth-first traversal. Changing strategy is explicit project policy, not an intake question or an executor optimization.

## User review contract

Before synthesis, the user confirms only the outcome ledger. After synthesis, the PRD writer presents a compact mapping from requirement/result to delivery branch, tracer evidence, first-proof role, and assumptions.

The review asks whether functionality, evidence, priority, assumptions, and scope were preserved. It does not ask the user to invent or approve low-level implementation mechanics.

## Acceptance criteria

The implementation is conformant when:

1. The grilling skill contains no question asking the user to define capabilities, branches, work packages, dependencies, tracer leaves, or Proof Slice topology.
2. Every required-now result has an actor, trigger, observable success, evidence, failure behavior, priority, constraints, and explicit assumptions before synthesis begins.
3. Generated nodes carry valid `source_requirements` lists.
4. Every outcome-bearing delivery branch has a primary tracer leaf with executable evidence.
5. A contained tracer uses normal traversal; only a cross-delivery-branch proof creates `proof_slice`.
6. Dependencies remain factual prerequisites.
7. The post-synthesis mapping review exposes coverage gaps and technical assumptions without turning them into attributed user requirements.

The detailed normative compilation rules are maintained in [`skills/wbs-prd/references/intake-to-wbs.md`](../skills/wbs-prd/references/intake-to-wbs.md). The node contract is maintained in [`skills/wbs-prd/references/node-schema.md`](../skills/wbs-prd/references/node-schema.md).

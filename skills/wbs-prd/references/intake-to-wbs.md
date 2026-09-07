# Outcome intake to WBS compilation

This is the normative boundary between user-facing discovery and internal WBS synthesis.

## Boundary rule

The intake discovers product truth in the user's language. It asks about actors, behavior, observable results, evidence, priorities, constraints, failures, and unknowns. It does not ask the user to design capabilities, branches, work packages, dependency graphs, tracer leaves, or Proof Slice membership.

Those structures are the PRD writer's technical representation of the answers. Ask a technical follow-up only when repository inspection cannot resolve a fact and the choice would materially change product behavior, cost, risk, or scope. Phrase the question in terms of that consequence.

## Intake output: outcome-requirement ledger

Assign stable IDs as requirements become clear. Maintain this ledger during the interview without showing internal WBS structure:

| Field | Meaning |
|---|---|
| ID | `REQ-###`, stable across revisions |
| Actor | Person or external system initiating or receiving the result |
| Trigger | Observable event or intent that starts the behavior |
| Result | Observable state or output when it succeeds |
| Evidence | Test, demonstration, measurement, or artifact that proves the result |
| Failure behavior | Observable handling of invalid, unavailable, or unsafe conditions |
| Priority | Required now, later, or explicitly out of scope |
| Constraints | Functional, policy, performance, security, or compatibility bounds |
| Open assumptions | Facts not established by the user or repository evidence |

Do not invent acceptance evidence. When the user cannot name it, recommend the smallest observable demonstration and ask whether that would count.

## Internal compilation

After the user confirms the outcome ledger:

1. Group related requirements around independently demonstrable results. Each coherent group becomes an outcome-bearing delivery branch, normally represented by a feature node.
2. Derive supporting capabilities and technical work packages from the behavior, evidence, constraints, existing architecture, and repository conventions. A leaf is one independently verifiable agent session.
3. Assign each generated node `source_requirements` IDs. A technical node may support several requirements; every in-scope requirement must reach at least one implementation leaf and one evidence-producing leaf.
4. Put shared structural work under the narrowest owning branch. Create a shared capability only when multiple delivery branches genuinely consume the same stable output; do not group work merely because it uses the same technical layer.
5. For each outcome-bearing branch, derive one ordinary `*-E2E` tracer leaf from the requirement's actor, trigger, result, failure behavior, and evidence. Its dependencies are the genuine branch interfaces required for that journey.
6. Mark exposed interfaces as provisional in context.md until their tracer passes. List known consumers so contract reconciliation is visible rather than hidden.
7. Select the smallest architectural proof from the highest-risk or highest-learning-value required outcome. If one branch tracer supplies it, use ordinary depth-first traversal. If it crosses delivery-branch ownership boundaries, compile the minimum dependency-closed leaves and tracer into `proof_slice`.
8. Keep dependency edges factual: data, sequence, or runtime prerequisites only. Never encode product priority or proof selection as fake dependencies.

## Compilation invariants

- Every required-now `REQ-*` maps to implementation and evidence.
- Every generated leaf cites at least one source requirement unless it is explicitly marked structural in `notes` and names the branches it enables.
- Every outcome-bearing delivery branch has exactly one primary tracer leaf. Additional scenario tests may exist, but one leaf owns the branch integration gate.
- Every tracer runs through the declared trigger-to-result boundary and covers material failure behavior; importing modules together is not sufficient.
- A tracer depends on every unresolved interface it composes, but not on unrelated documentation, administration, or future enhancement work.
- A Proof Slice references existing leaves and never changes their parentage.
- Open product questions remain open. Technical assumptions are recorded and surfaced; they are not presented as user decisions.

## Mapping review

After synthesis, present a compact traceability table:

| Requirement/result | Derived delivery branch | Tracer evidence | First-proof role | Assumptions |
|---|---|---|---|---|

Ask the user to confirm that the derived plan preserves the requested functionality, priorities, evidence, and scope. Do not ask them to approve implementation details they did not specify. If they challenge a branch or tracer, translate the issue back to outcome coverage and revise the technical mapping.

## Question translation examples

| Do not ask during intake | Ask instead |
|---|---|
| Which features are coherent delivery branches? | Which useful result can be demonstrated independently? |
| What should the E2E leaf depend on? | What must be working for that result to count as real? |
| Is this a cross-capability Proof Slice? | Which journey should work first before we invest in the rest? |
| Is this interface provisional? | Which external behavior may still change, and who would be affected? |
| What are the API work packages? | What information enters, what result comes back, and what failures must users see? |

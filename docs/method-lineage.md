# Method lineage

The outcome-driven WBS method descends from the test-driven, specification-first
tradition: acceptance-driven development, the EARS requirements syntax, and the
walking-skeleton / tracer-bullet school of integration. This note maps each of
those concepts onto its artifact here so a reader who knows the classic practice
can locate the equivalent immediately — and names where this system deliberately
extends or diverges. The normative rules live in the
[Outcome-Driven WBS Specification](outcome-driven-specification.md); the
operational detail lives in the [User Guide](user-guide.md).

## Concept mapping

| Classic practice | This toolkit | Where it lives |
|---|---|---|
| EARS-style acceptance criteria — "When \<trigger\>, the system shall \<result\>" | Outcome-requirement ledger: `REQ-###` rows with actor, trigger, observable result, evidence, failure behavior, priority, constraints, open assumptions | `.wbs/context.md` `## Outcome Requirements`, captured during the grilling phase |
| EARS unwanted-behavior form — "If \<condition\>, then \<response\>" | The ledger's `Failure behavior` column, a first-class field | same rows |
| Coarse architecture designed once, up front (the `design.md` of spec-driven development: module boundaries, backend shape, tech stack) | Synthesis-time context: Tech Stack, Core Design Concepts, Architecture Notes, Delivery Branches — compiled only after the user confirms the outcome ledger, before any code | `.wbs/context.md` |
| Fine-grained design one failing test ahead | Per-leaf execution: `outputs` is the node's exact interface, `acceptance_criteria` become tests before implementation exists | `wbs-exec` loop |
| Red-green: write the failing test first, watch it fail for the right reason | "Translate every `acceptance_criteria` item into a failing test before writing any implementation… confirm they fail for the right reason." Spec-time `verify` entries deliberately reference test files that do not exist yet | `wbs-exec` step 2 |
| Vertical slice / tracer bullet — one thin path through every real layer | The `*-E2E` tracer leaf: runs from the declared trigger through real composed interfaces to the observable result; mocking only external transports | node schema, one per outcome-bearing branch |
| Walking skeleton — first end-to-end slice that proves the architecture can deliver | The Proof Slice: minimum dependency-closed cross-branch leaf set, one end-to-end `verify`, and a `hypothesis` naming the architectural assumption under test | `tree.yaml` `proof_slice` + `wbs.py` gate |
| Tests define behavior; design defines boundaries | Dependencies are factual prerequisites only, never priority signals; verification supplies evidence while explicit human approval authorizes broader execution | throughout |
| Architecture decision records | `## Design Alternatives`: one-line pruned paths with a do-not-re-litigate rule at execution time | `.wbs/context.md` |
| Emergent, refactored-toward design | Interfaces marked provisional until their tracer passes, with known consumers listed; capability-checkpoint integrity pass; `## Learnings` for spec co-evolution | `context.md` + `wbs-exec` |

## The ledger is EARS in structured form

The outcome-requirement ledger carries the semantics of EARS without the
constrained sentence syntax. Trigger plus result is the event-driven form;
failure behavior is the unwanted-behavior form. It is a deliberate superset:
evidence, priority, and open assumptions are mandatory fields — "do not invent
acceptance evidence" is a stronger rule than anything in EARS itself — and
priority replaces the optional-feature form as a first-class dimension.

The two EARS forms without a dedicated column fold in naturally:

- state-driven ("While \<state\>, the system shall…") becomes a constraint on
  the result;
- optional-feature ("Where \<feature\>, the system shall…") becomes the
  priority field (required now / later / out of scope).

The trade-off is real: EARS's fixed templates mechanically disambiguate, while
ledger cells remain free prose. Here that load is carried by intake discipline
instead — observable triggers, observable results, and failure behavior that
can be tested without asking the author. The validator's refusal of leaves
without testable acceptance criteria is the enforcement point.

## Two design altitudes, three grains

Classic test-driven architecture advice separates the coarse design (module and
backend boundaries, decided deliberately and once) from the fine design (module
internals, allowed to emerge one failing test at a time). This system keeps
that split and makes the timing mechanical:

1. **Coarse, once:** synthesis compiles the confirmed ledger into delivery
   branches, provisional interfaces, tracers, and any Proof Slice — before any
   code exists.
2. **Fine, just-in-time:** each leaf's `outputs` fixes exactly the surface to
   build; its criteria become the failing tests.
3. **Reconciled continuously:** provisional interfaces remain revisable until
   their tracer passes; when the tracer establishes a different contract,
   affected consumers and their tests are reworked coherently and the change is
   recorded.

It then splits work into three grains rather than two altitudes: a leaf is the
execution unit for one agent session; an outcome-bearing feature branch is the
delivery and integration unit; a Proof Slice is a cross-branch authorization
unit. None of these is a fourth hierarchy — the tree stays self-similar.

## What the Proof Slice adds to the walking skeleton

A branch tracer is the classic vertical slice scoped to one delivery branch.
The Proof Slice exists only when the smallest architectural proof crosses
delivery-branch ownership boundaries — the situation where a walking skeleton
must be assembled from several branches' leaves at once. Its `hypothesis`
field records the architectural assumption being tested, making explicit that
the proof tests boundaries, not requirements: a ledger row can pass against an
in-memory fake; the proof cannot.

The state machine separates evidence from authorization. `verified` means the
end-to-end command passed; execution still halts until a human runs
`approve-proof`, which re-runs the verification before unlocking ordinary
traversal. Classic TDD has no such gate — it is the AI-development-cycle
addition: an agent may verify, but only the owner authorizes.

## Deliberate divergences

1. **Bottom-up is allowed inside a branch.** Classic tracer advice is to fire
   the tracer first; here only the first architectural proof must precede
   broader execution. After approval, a branch may be built leaf-by-leaf
   bottom-up and closed by its `*-E2E` tracer. The accepted risk is later
   discovery of a broken branch boundary; the mitigation is the provisional
   interface list with named consumers, which makes contract churn visible.
2. **Refactor is not a named loop step.** The execution loop is tests-first →
   implement → gate → close. The refactoring role is carried at a coarser
   cadence instead: the Definition-of-Done gate keeps the whole suite green on
   every completion, and the capability checkpoint runs an integrity pass over
   a `CAP-*` subtree when completion propagates to it.
3. **Spec co-evolution is explicit machinery.** When implementation reveals a
   wrong assumption, the executor blocks with the reason and proposes a tree or
   context edit rather than silently restructuring — the spec is treated as
   refactable code with a single writer, dated in `## Learnings`.

## Related

- [Outcome-Driven WBS Specification](outcome-driven-specification.md) — the
  normative intake, synthesis, and proof-selection rules.
- [User Guide](user-guide.md) — the node schema, execution loop, and command
  reference.
- EARS: Mavin et al., "Easy Approach to Requirements Syntax"; walking
  skeleton: Cockburn; tracer bullets: Hunt & Thomas, *The Pragmatic
  Programmer*.

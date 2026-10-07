# Module Design in a WBS

The coding rules themselves (deep modules, one owner per concern, the red-flag table) are global and live outside this toolkit. Read the first that exists:

1. `~/.aai/rules/coding.md` (the owner's global rules)
2. `.ailib/dev-rules/rules/coding.md` (vendored into this project)
3. the ambient library's `library/dev-rules/rules/coding.md`

This file adds only what is specific to the WBS method: where those rules attach to WBS artifacts and what the executor checks before `done`. The PRD writer applies it when deriving `## Module Boundaries` in `.wbs/context.md`; the executor applies it when implementing a leaf and at each capability checkpoint. Projects may tighten the rules in their own context.md; they may not silently loosen them.

## Mapping to WBS artifacts

- **`## Module Boundaries` in context.md** is the authoritative module map: each module's owned concern, public interface, and what it hides. Code that does not fit an entry is either a missing entry (propose it) or misplaced code (move it).
- **A leaf's `outputs` is its public surface.** Build exactly that surface; everything else is private by the language's convention (`_name`, unexported, `__all__`, package-private). Adding public surface not named in `outputs` requires a context.md or tree correction, not a silent addition.
- **A leaf extends its owning module.** When a leaf's work belongs to a concern that already has an owner, implement it inside that owner rather than creating a parallel module beside it.
- **Provisional interfaces.** Until a branch tracer passes, a declared interface may change; when it does, reconcile consumers to the better contract. Never preserve a shallow or leaky provisional shape with an unrequested compatibility layer.
- **Tests exercise public interfaces.** Acceptance tests call the module through its declared surface. A test that must reach into private state to verify behavior signals a missing operation or a leaked concern.

## Executor checks

Before calling `wbs.py done`, confirm for the changed code:

- [ ] Every new or changed public name is in the leaf's `outputs` or the module's declared interface.
- [ ] No module imports another module's private names or internal data shapes.
- [ ] No new pass-through wrapper, shallow module, or caller-required call sequence.
- [ ] Logic touching a concern lives in that concern's owning module.
- [ ] Entry points only parse input, call one domain operation, and format output.

A violation the leaf cannot fix within its scope is reported, not hidden: append it to context.md `## Learnings` and propose the boundary or tree correction to the user.

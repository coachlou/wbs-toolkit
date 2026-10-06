# Module Design Rules

The canonical design constraints for code produced through a WBS. The PRD writer applies them when it derives `## Module Boundaries` in `.wbs/context.md`; the executor applies them when it implements a leaf and at each capability checkpoint. Projects may tighten these rules in their own context.md; they may not silently loosen them.

## Principles

1. **Deep modules.** A module's interface is the cost it imposes on every caller; its implementation is the value it hides from them. Maximize the ratio. A small public surface must hide substantial behavior: policy, sequencing, error recovery, caching, persistence, format details.
2. **One owned concern per module.** Each concern—a domain concept, an external system, a data store, a policy—has exactly one owning module. Other code reaches it only through that module's public interface.
3. **Information hiding over task decomposition.** Draw boundaries around design decisions likely to change (storage format, vendor API, algorithm), not around the order steps execute in. A module per pipeline stage that shares one data shape leaks that shape everywhere.
4. **Pull complexity down.** When a choice can be made correctly inside the module—defaults, retries, normalization, edge cases—make it there. Do not export a configuration option, flag, or ordering requirement to callers to avoid deciding.
5. **Dependencies point toward stability.** Entry points (CLI, HTTP handlers, UI) depend on domain modules; domain modules depend on abstractions of infrastructure, not on entry points. No import cycles.

## Red flags — treat as defects

| Flag | Symptom | Correct move |
|---|---|---|
| Shallow module | Interface is about as complex as its implementation | Merge into its caller or into the module that owns the concern |
| Pass-through | Method or wrapper only forwards arguments to another layer | Remove the layer, or give it a real responsibility |
| Leaked internals | Callers import private names, read internal fields, or depend on internal data shapes | Expose an intention-revealing operation; keep the shape private |
| Split concern | Same knowledge (format, rule, query) encoded in two modules | Move it to the single owner; callers ask the owner |
| Caller-side sequencing | Callers must invoke A before B or the module misbehaves | Fold the sequence into one operation |
| Option creep | New boolean or mode parameter added to serve one caller | Decide internally, or create a distinct operation with its own name |
| Logic in entry points | Business rules inside CLI, route, or UI handlers | Move them into the owning domain module; keep the entry point a thin adapter |
| Generic dumping ground | `utils`, `helpers`, `common`, `misc` accumulating unrelated code | Move each function to the module whose concern it serves |

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

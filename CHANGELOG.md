# Changelog

## 0.3.0 - 2026-10-07

### Added

- Add `skills/wbs-exec/references/module-design.md`: how the global coding rules (`~/.aai/rules/coding.md`, published by the ambient library's `dev-rules` capability) attach to WBS artifacts, plus executor checks. The rules themselves are not copied into the toolkit.
- Add `## Module Boundaries` to the `context.md` contract and `init` scaffold: one owning module, public interface, and hidden decisions per concern.
- `wbs-prd` derives the module map during synthesis; `wbs-exec` builds inside owning modules, checks the diff before `done`, and scans capability checkpoints for design red flags.
- `.aai` identity and instructions templates name the design rules as a project ground rule.
- `distro/DEPENDS` adds `dev-rules`, so installing the toolkit vendors the global coding rules at `.ailib/dev-rules/` for folders without the owner's `~/.aai`.

## 0.2.2 - 2026-09-09

### Docs

- Add `docs/method-lineage.md`: the concept mapping between the outcome-driven WBS method and classic TDD / EARS / walking-skeleton practice, and the deliberate divergences. Linked from the README and user guide; included in the deterministic distro and the ambient-library `app/docs/` snapshot.

## 0.2.1 - 2026-09-07

### Fixed

- Reject malformed acceptance criteria and verification command lists before execution.
- Require every executable leaf to have an effective node-level or project-level verification gate.
- Write WBS state through atomic file replacement.
- Copy the bundled node schema into clean projects during `init`.
- Correct the quick start, traversal, completion, status, and decomposition documentation.
- Document the trusted-command and single-writer state boundaries.

### Release engineering

- Add a version source and an allowlist-based deterministic distro builder.
- Generate a release manifest, ZIP checksum, and clean-room smoke-test the assembled toolkit.
- Exclude repository state, chat exports, experiments, caches, previous distributions, and unrelated artifacts from the core toolkit.

## 0.2.0 - 2026-09-06

### Added

- Make Proof-Slice-first execution the default while retaining selectable legacy bottom-up traversal.
- Add proof verification and explicit human approval before broader execution.
- Add outcome-driven intake, requirement traceability, branch tracers, comparison tooling, and paired-pilot evidence.

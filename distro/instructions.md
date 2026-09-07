# wbs-toolkit

Makes a software project an outcome-driven WBS workspace. It turns confirmed
user results into a traceable work tree, executes verified leaf work through an
AI coding agent, and requires explicit approval when a cross-branch Proof Slice
has demonstrated the first architectural journey.

The capability vendors a pinned snapshot of the Python CLI, the PRD and
execution skills, documentation, and schema under `app/`. It does not run a
server, retain API credentials, or create a second application runtime.

## Important

- **Python 3.10+ is required; `uv` is preferred.** The launcher invokes
  `uv run --with pyyaml` when available; its Python-only fallback requires
  `PyYAML` already installed.
- **`done` and `approve-proof` execute declared shell verification commands.**
  Use them only in a trusted project after reviewing the WBS verification list.
- Never edit `.ailib/wbs-toolkit/`; update it by re-running the installer.
  Personalize behavior by copying it to `.aai/skills/wbs-toolkit/`.

## Install — make a project a WBS workspace

With the ambient library plugin installed:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/library/ambient-folder/install.sh" \
  wbs-toolkit --check <target-project>
bash "${CLAUDE_PLUGIN_ROOT}/library/ambient-folder/install.sh" \
  wbs-toolkit <target-project>
```

The first command is a no-write plan. Confirm the target path before the second
command. The installer writes the following contract:

```text
<target-project>/
├── .aai/                         # owned: never overwritten by updates
│   ├── identity.md
│   ├── instructions.md
│   └── context.md
├── .ailib/                       # vendored: re-synced by updates
│   ├── ambient-folder/
│   ├── wbs-toolkit/
│   │   └── app/                  # pinned CLI, skills, schema, docs
│   └── manifest.yaml
├── wbs.sh                        # launcher into the resolved capability
├── CLAUDE.md, AGENTS.md          # appended discovery anchors
└── .wbs/                         # created by `wbs.sh init` or the PRD skill
```

Verify with:

```bash
ls <target-project>/.aai <target-project>/.ailib/wbs-toolkit
bash <target-project>/wbs.sh --help
```

## Operate — inside an installed project

The project’s `.aai/instructions.md` governs day-to-day behavior. In short:

1. Ask for a requirements interview with the vendored `app/skills/wbs-prd/`
   skill, or initialize from an existing PRD:

   ```bash
   bash wbs.sh init docs/prd.md
   ```

2. Inspect and execute one eligible leaf at a time:

   ```bash
   bash wbs.sh next
   bash wbs.sh start <node-id>
   # implement and review the returned work package
   bash wbs.sh done <node-id>
   ```

3. If `done` returns `awaiting_proof_approval`, review the integrated evidence
   with the owner before running `bash wbs.sh approve-proof`.

4. Use `bash wbs.sh status` to inspect progress, strategy, and Proof Slice
   state. Use `bash wbs.sh strategy legacy_bottom_up` only when the owner
   explicitly selects the compatibility traversal.

Re-run the ambient-folder installer to update. It refreshes `.ailib/` and keeps
the project’s `.aai/` profile and `.wbs/` state untouched.

## Maintain — library owners

`distro/` in the WBS source repository is the package source. The canonical
`library/wbs-toolkit/` directory is its build output and must not be edited by
hand. Sync with:

```bash
scripts/sync-distro.sh wbs-toolkit /path/to/recursive-development
```

Then run the ambient-library audits and promote through its normal release path.

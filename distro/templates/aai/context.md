# Context — {{NAME}}

| Path | What it is | Read when |
|---|---|---|
| `.aai/instructions.md` | this project’s WBS operating behavior | always, first |
| `.aai/identity.md` | project identity and WBS ground rules | always |
| `.aai/skills/wbs-toolkit/` | a project-specific WBS capability fork, if present | resolving the capability; shadows `.ailib/` |
| `wbs.sh` | stable project-root WBS launcher | running any WBS command |
| `.wbs/tree.yaml` | WBS specification and live single-writer state | scheduling, status, or mutation |
| `.wbs/context.md` | implementation context for every leaf | before coding or review |
| `.wbs/node-template.yaml` | local node-schema reference | manually editing or diagnosing the tree |
| `.ailib/wbs-toolkit/` | pristine vendored toolkit and pinned `app/` snapshot | updating or comparing a fork |
| `.ailib/manifest.yaml` | vendored capability provenance and version | checking installed version |

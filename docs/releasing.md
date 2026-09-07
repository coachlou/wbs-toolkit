# Release process

The recipient is a developer or AI coding agent installing the WBS toolkit into a project. A release is complete only when that recipient can extract the archive, initialize a clean project, find the schema template, validate a populated tree, and run the focused toolkit tests.

## Core distro boundary

The deterministic builder includes only:

- `README.md`, `LICENSE.md`, `CHANGELOG.md`, and `VERSION`;
- `wbs.py` and `.wbs/node-template.yaml`;
- recipient-facing `docs/`;
- `wbs-prd`, `wbs-exec`, and their references;
- the focused WBS runtime tests.

The core distro excludes live repository WBS state, chat exports, experiments and raw pilot evidence, local settings, caches, prior archives, and unrelated artifacts. Experimental evidence remains available in the source repository and may be published as a separate evidence package.

## Preconditions

1. Choose and add `LICENSE.md`. The builder refuses to create an externally distributable artifact without it.
2. Update `VERSION` and `CHANGELOG.md` together.
3. Commit the exact release contents and create an annotated tag with the matching `v<version>` name.
4. Run all source checks before building.

## Build

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_wbs tests.test_scheduler_benchmark tests.test_release_builder
ruff check --no-cache wbs.py scripts/build_release.py tests
python3 scripts/build_release.py --ref v0.2.1
```

The builder reads only committed blobs from the requested ref. Working-tree changes and untracked files cannot leak into the output. It creates:

```text
dist/wbs-toolkit-<version>-<short-sha>/
dist/wbs-toolkit-<version>-<short-sha>.zip
dist/wbs-toolkit-<version>-<short-sha>.zip.sha256
```

The expanded directory and ZIP contain `RELEASE-MANIFEST.json` with the source commit and a SHA-256 digest for every packaged file. ZIP timestamps and permissions are normalized for reproducibility.

## Publication gate

Before publishing, verify that the tag resolves to the manifest commit, recompute the ZIP checksum, inspect the archive listing, and confirm the remote destination. Never move an already-published tag; issue a patch release instead.

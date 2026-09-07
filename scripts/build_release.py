#!/usr/bin/env python3
"""Build a deterministic, allowlist-based WBS toolkit distribution from Git."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


REQUIRED_FILES = {
    ".wbs/node-template.yaml",
    "CHANGELOG.md",
    "LICENSE.md",
    "README.md",
    "VERSION",
    "docs/outcome-driven-specification.md",
    "docs/user-guide.md",
    "tests/test_wbs.py",
    "wbs.py",
}
ALLOWED_PREFIXES = ("skills/",)
FORBIDDEN_PARTS = {
    ".DS_Store",
    ".claude",
    ".git",
    ".herenow",
    ".ruff_cache",
    "__pycache__",
    "chat_exports",
    "dist",
    "experiments",
}
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def run_git(root: Path, *args: str, text: bool = True):
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=text, check=False
    )
    if result.returncode:
        error = result.stderr.strip() if text else result.stderr.decode().strip()
        raise RuntimeError(error or f"git {' '.join(args)} failed")
    return result.stdout


def select_release_files(tracked_files: list[str]) -> list[str]:
    selected = sorted(
        path
        for path in tracked_files
        if path in REQUIRED_FILES or path.startswith(ALLOWED_PREFIXES)
    )
    missing = sorted(REQUIRED_FILES - set(selected))
    if missing:
        raise ValueError("required release files missing: " + ", ".join(missing))
    forbidden = [
        path
        for path in selected
        if any(part in FORBIDDEN_PARTS for part in Path(path).parts)
    ]
    if forbidden:
        raise ValueError("forbidden release files selected: " + ", ".join(forbidden))
    return selected


def git_blob(root: Path, ref: str, path: str) -> bytes:
    return run_git(root, "show", f"{ref}:{path}", text=False)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_zip(zip_path: Path, package_name: str, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(f"{package_name}/{path}", ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[path])


def smoke_test(package_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(package_dir / "wbs.py"), "--help"],
        cwd=package_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "tests.test_wbs"],
        cwd=package_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    with tempfile.TemporaryDirectory(prefix="wbs-release-smoke-") as temp_dir:
        target = Path(temp_dir)
        prd = target / "prd.md"
        prd.write_text("# Release smoke project\n")
        subprocess.run(
            [sys.executable, str(package_dir / "wbs.py"), "init", str(prd)],
            cwd=target,
            capture_output=True,
            text=True,
            check=True,
        )
        for relative in (".wbs/tree.yaml", ".wbs/context.md", ".wbs/node-template.yaml"):
            if not (target / relative).is_file():
                raise RuntimeError(f"clean-room init did not create {relative}")


def build_release(root: Path, ref: str, output_dir: Path) -> tuple[Path, Path]:
    commit = run_git(root, "rev-parse", f"{ref}^{{commit}}").strip()
    tracked = run_git(root, "ls-tree", "-r", "--name-only", ref).splitlines()
    selected = select_release_files(tracked)
    files = {path: git_blob(root, ref, path) for path in selected}

    version = files["VERSION"].decode().strip()
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"VERSION must be stable SemVer X.Y.Z, got {version!r}")
    if ref.startswith("v") and ref[1:] != version:
        raise ValueError(f"tag {ref!r} does not match VERSION {version!r}")

    package_name = f"wbs-toolkit-{version}-{commit[:7]}"
    package_dir = output_dir / package_name
    zip_path = output_dir / f"{package_name}.zip"
    checksum_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    collisions = [path for path in (package_dir, zip_path, checksum_path) if path.exists()]
    if collisions:
        raise FileExistsError("release output already exists: " + ", ".join(map(str, collisions)))

    manifest = {
        "name": "wbs-toolkit",
        "version": version,
        "source_ref": ref,
        "source_commit": commit,
        "files": [
            {"path": path, "sha256": sha256(files[path]), "size": len(files[path])}
            for path in sorted(files)
        ],
    }
    files["RELEASE-MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".wbs-release-stage-", dir=output_dir) as stage:
        stage_root = Path(stage)
        staged_package = stage_root / package_name
        staged_zip = stage_root / zip_path.name
        staged_checksum = stage_root / checksum_path.name
        for path, content in files.items():
            destination = staged_package / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        write_zip(staged_zip, package_name, files)
        staged_checksum.write_text(
            f"{sha256(staged_zip.read_bytes())}  {zip_path.name}\n"
        )
        smoke_test(staged_package)
        staged_package.replace(package_dir)
        staged_zip.replace(zip_path)
        staged_checksum.replace(checksum_path)
    return package_dir, zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Committed Git ref to package")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        package_dir, zip_path = build_release(root, args.ref, args.output)
    except (FileExistsError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"release build failed: {exc}\n")
    print(json.dumps({"package_dir": str(package_dir), "zip": str(zip_path)}, indent=2))


if __name__ == "__main__":
    main()

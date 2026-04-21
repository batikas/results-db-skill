#!/usr/bin/env python3
"""
package_skill.py — Create a release archive for the results-db skill repo.

The archive is intended for GitHub release uploads or marketplace packaging.
It includes the repository contents needed to recreate the published skill.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def should_exclude(path: Path) -> bool:
    if ".git" in path.parts:
        return True
    if "__pycache__" in path.parts:
        return True
    if "dist" in path.parts:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the skill repo into a .skill archive.")
    parser.add_argument("--repo-root", default=".", help="Repository root to package.")
    parser.add_argument("--output", default="", help="Output .skill path. Defaults to dist/<repo>-v<VERSION>.skill.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    version = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
    default_output = repo_root / "dist" / f"results-db-skill-v{version}.skill"
    out = Path(args.output).expanduser().resolve() if args.output else default_output
    out.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(out, "w", compression=ZIP_DEFLATED) as zf:
        for path in sorted(repo_root.rglob("*")):
            if path.is_dir() or should_exclude(path.relative_to(repo_root)):
                continue
            zf.write(path, path.relative_to(repo_root))

    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

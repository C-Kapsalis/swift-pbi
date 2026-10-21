"""Vendor the four pinned tools into the benchmark sandbox, offline.

The eval sandbox has no network and an empty package cache, so
`uvx --from git+https://github.com/...` cannot resolve and even
`uvx --from <local path>` cannot build: the build backend (hatchling) is not
cached there either. The agent would then read the files by hand, and the
benchmark would measure the harness instead of the skills.

This script builds a **complete virtual environment** with the four pinned
tools — while the real package cache is still available — and copies it
into the sandbox. The venv is relocatable, and a `tools/tools.sh` points the
four variables the skills use at its executables.

    python3 -I vendor_tools.py <out-folder> [<repo-root> ...]

Each repo root defaults to the one under `~/Documents/GitHub/`:

    tmdl-preflight/tmdl-preflight
    tmdl-drift-doctor/tmdl-drift-doctor
    pbip-model-forge/pbip-model-forge
    pbi-plot-styler/pbi-plot-styler

Each repo is exported at its pinned `v1.1.0` tag, so the sandbox runs
exactly what the plugin's pins install. Git, uv and the standard library
only.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

TAG = "v1.1.0"

DEFAULT_REPOS = [
    "tmdl-preflight/tmdl-preflight",
    "tmdl-drift-doctor/tmdl-drift-doctor",
    "pbip-model-forge/pbip-model-forge",
    "pbi-plot-styler/pbi-plot-styler",
]

HOME = Path.home()
GITHUB = HOME / "Documents" / "GitHub"

TOOLS = {
    "tmdl-preflight": "tmdl-preflight",
    "tmdl-drift-doctor": "drift-doctor",
    "pbip-model-forge": "pbip-forge",
    "pbi-plot-styler": "pbi-plot-styler",
}


def export(repo: Path, dest: Path) -> None:
    """Export `repo`'s pinned tag into `dest` (a tree, no .git)."""
    if not (repo / ".git").exists():
        raise SystemExit(f"vendor_tools: {repo} is not a git repository")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", TAG],
        capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(
            f"vendor_tools: cannot export {TAG} from {repo}: "
            f"{proc.stderr.decode(errors='replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        tar.extractall(dest)


def build_venv(sources: list, venv: Path) -> None:
    """A virtual environment with every tool installed, offline."""
    if venv.exists():
        shutil.rmtree(venv)
    subprocess.run(["uv", "venv", "--python", "3.12", str(venv)], check=True,
                   capture_output=True)
    env = dict(os.environ, VIRTUAL_ENV=str(venv))
    for source in sources:
        proc = subprocess.run(
            ["uv", "pip", "install", "--offline", str(source)],
            env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(
                f"vendor_tools: cannot install {source.name} into the venv:\n"
                f"{proc.stdout}\n{proc.stderr}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve()
    roots = [Path(p).resolve() for p in sys.argv[2:] if p.strip()]
    if not roots:
        roots = [GITHUB / r for r in DEFAULT_REPOS]

    out.mkdir(parents=True, exist_ok=True)
    src = out / "src"
    src.mkdir(parents=True, exist_ok=True)
    sources = []
    for repo in roots:
        dest = src / repo.name
        export(repo, dest)
        sources.append(dest)

    venv = out / "venv"
    build_venv(sources, venv)

    lines = [
        "# The four pinned tools, installed offline into one virtual",
        "# environment. The eval sandbox has no network and an empty package",
        "# cache, so `uvx --from git+https://...` cannot resolve and a local",
        "# install cannot build either. The environment is built here, while",
        "# the real package cache is still available.",
        "",
        f'VENV="{venv}"',
        "",
    ]
    for dist, exe in TOOLS.items():
        lines.append(f'{exe.upper().replace("-", "_")}="$VENV/bin/{exe}"')
    lines += [
        "",
        'PREFLIGHT="$VENV/bin/tmdl-preflight"',
        'FORGE="$VENV/bin/pbip-forge"',
        'DRIFT="$VENV/bin/drift-doctor"',
        'STYLER="$VENV/bin/pbi-plot-styler"',
        "",
    ]
    (out / "tools.sh").write_text("\n".join(lines), encoding="utf-8")
    print(f"tools vendored into {out}")


if __name__ == "__main__":
    main()

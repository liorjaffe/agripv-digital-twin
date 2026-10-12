"""Shared provenance metadata for generated project artifacts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def build_artifact_metadata() -> dict[str, str | bool]:
    """Return the source revision and whether tracked or untracked edits exist."""
    revision = os.environ.get("GITHUB_SHA")
    if not revision:
        revision = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        "source_commit": revision,
        "working_tree_dirty": bool(status.strip()),
    }

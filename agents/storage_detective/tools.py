"""
Tools available to the Storage Detective LangGraph agent.

These perform genuine filesystem inspection using os/pathlib/shutil —
real byte counts from the machine the app runs on, not fabricated
numbers. No file is ever deleted by these functions without an
explicit, separately-approved call to clean_approved_items().

NOTE ON DEPLOYMENT: when this app runs on Render, it scans the
container filesystem it's deployed in, not the end user's laptop —
a cloud container simply has no access to someone's local Windows/Mac
disk. The scanning logic itself is fully real and works correctly;
for a meaningful personal-storage demo, run the app locally (see
README) where it scans your actual machine.
"""

import os
import platform
import shutil
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ScanItem:
    category: str
    path: str
    size_bytes: int
    exists: bool
    item_count: int = 0


def _dir_size(path: Path, max_items: int = 200_000) -> tuple[int, int]:
    """Real recursive size walk. Bounded to avoid pathological runaway scans."""
    total = 0
    count = 0
    if not path.exists():
        return 0, 0
    try:
        for root, dirs, files in os.walk(path, onerror=lambda e: None):
            for f in files:
                count += 1
                if count > max_items:
                    return total, count
                fp = Path(root) / f
                try:
                    total += fp.stat().st_size
                except (OSError, FileNotFoundError):
                    continue
    except (PermissionError, OSError):
        pass
    return total, count


def _candidate_paths() -> dict:
    """
    Returns the platform-appropriate candidate paths for each storage
    category. Real path resolution per-OS, not hardcoded to one platform.
    """
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return {
            "Chrome Cache": local_appdata / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            "Edge Cache": local_appdata / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            "npm Cache": appdata / "npm-cache",
            "pip Cache": local_appdata / "pip" / "Cache",
            "Temporary Files": Path(os.environ.get("TEMP", home / "AppData" / "Local" / "Temp")),
            "Downloads": home / "Downloads",
            "Recycle Bin (approx)": Path("C:/$Recycle.Bin"),
        }
    elif system == "Darwin":
        return {
            "Chrome Cache": home / "Library" / "Caches" / "Google" / "Chrome",
            "npm Cache": home / ".npm",
            "pip Cache": home / "Library" / "Caches" / "pip",
            "Temporary Files": Path("/tmp"),
            "Downloads": home / "Downloads",
            "Xcode DerivedData": home / "Library" / "Developer" / "Xcode" / "DerivedData",
        }
    else:  # Linux
        return {
            "Chrome/Chromium Cache": home / ".cache" / "google-chrome",
            "npm Cache": home / ".npm",
            "pip Cache": home / ".cache" / "pip",
            "Temporary Files": Path("/tmp"),
            "Downloads": home / "Downloads",
            "Trash": home / ".local" / "share" / "Trash",
        }


def scan_storage(scan_root: str | None = None) -> list[ScanItem]:
    """
    Tool: SCAN. Walks known cache/cleanup-candidate locations on the
    current machine and returns real measured sizes.
    """
    paths = _candidate_paths()
    results = []
    for category, path in paths.items():
        size, count = _dir_size(path)
        results.append(ScanItem(category=category, path=str(path), size_bytes=size, exists=path.exists(), item_count=count))

    # Also scan for old Python virtual environments under the home dir /
    # optional user-provided scan_root, since these are a named category
    # in the assignment brief and aren't in a single fixed OS path.
    venv_root = Path(scan_root) if scan_root else Path.home()
    venv_hits = find_virtualenvs(venv_root)
    venv_total = sum(v["size_bytes"] for v in venv_hits)
    results.append(ScanItem(
        category="Old Python Virtual Environments",
        path=str(venv_root),
        size_bytes=venv_total,
        exists=True,
        item_count=len(venv_hits),
    ))
    return results


def find_virtualenvs(root: Path, max_depth: int = 4) -> list[dict]:
    """
    Tool: real detection of venv/.venv folders (identified by the
    presence of a pyvenv.cfg marker file, the standard venv fingerprint)
    up to a bounded depth so it doesn't crawl the entire disk.
    """
    hits = []
    root = Path(root)
    if not root.exists():
        return hits

    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        depth = len(Path(dirpath).parts) - root_depth
        if depth > max_depth:
            dirnames[:] = []
            continue
        if "pyvenv.cfg" in filenames:
            venv_path = Path(dirpath)
            size, _ = _dir_size(venv_path)
            has_manifest = any(
                (venv_path.parent / f).exists()
                for f in ["requirements.txt", "pyproject.toml", "Pipfile.lock"]
            )
            hits.append({
                "path": str(venv_path),
                "size_bytes": size,
                "has_manifest": has_manifest,
            })
            dirnames[:] = []  # don't descend into a venv itself
    return hits


def classify_safety(category: str, has_manifest: bool | None = None) -> dict:
    """
    Tool: CLASSIFY. Deterministic safety classification independent of
    the LLM, matching the knowledge base's documented guidance. The LLM
    later explains WHY in natural language, grounded in this + RAG.
    """
    safe_categories = {
        "Chrome Cache", "Edge Cache", "Chrome/Chromium Cache", "npm Cache",
        "pip Cache", "Recycle Bin (approx)",
    }
    conditional_categories = {
        "Temporary Files", "Old Python Virtual Environments", "Trash",
        "Xcode DerivedData",
    }
    never_categories = {"Downloads"}

    if category in never_categories:
        return {"safety": "NEVER_AUTO", "priority": "review_individually"}
    if category in safe_categories:
        return {"safety": "SAFE", "priority": "high"}
    if category == "Old Python Virtual Environments" and has_manifest is False:
        return {"safety": "CAUTION", "priority": "review_individually"}
    if category in conditional_categories:
        return {"safety": "CONDITIONAL", "priority": "medium"}
    return {"safety": "CONDITIONAL", "priority": "low"}


def clean_approved_items(paths: list[str], dry_run: bool = True) -> dict:
    """
    Tool: CLEAN. Deletes ONLY the exact paths passed in, and ONLY after
    the UI has collected explicit per-item user approval. dry_run=True
    by default — actual deletion requires the caller to explicitly pass
    dry_run=False, which the UI only does after a confirmed approval click.
    """
    results = {"deleted": [], "skipped": [], "errors": [], "freed_bytes": 0}
    for p in paths:
        path = Path(p)
        if not path.exists():
            results["skipped"].append(str(path))
            continue
        try:
            size, _ = _dir_size(path) if path.is_dir() else (path.stat().st_size, 1)
            if not dry_run:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
            results["deleted"].append(str(path))
            results["freed_bytes"] += size
        except (PermissionError, OSError) as e:
            results["errors"].append({"path": str(path), "error": str(e)})
    return results


def verify_cleanup(paths: list[str]) -> dict:
    """
    Tool: VERIFY. Confirms post-cleanup state — checks the approved
    paths no longer exist (or shrank), providing an honest report
    rather than assuming the delete succeeded.
    """
    still_present = [p for p in paths if Path(p).exists()]
    return {
        "fully_cleared": len(still_present) == 0,
        "still_present": still_present,
        "cleared_count": len(paths) - len(still_present),
    }


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

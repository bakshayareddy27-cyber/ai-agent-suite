# Storage Locations Reference — Safety & Recovery Notes

## Browser Caches (Chrome, Firefox, Edge)
Location (Windows): `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache`, similar paths for Edge/Firefox.
Location (Linux/Mac): `~/.cache/google-chrome/`, `~/Library/Caches/Google/Chrome/`.
Safety: Completely safe to delete. This is a local performance cache of previously-downloaded web assets (images, scripts, stylesheets) — the browser will simply re-download what it needs on next visit. No user data, passwords, bookmarks, or history is stored here. Deleting it may cause slightly slower page loads on first re-visit to sites, nothing more. Recommended cleanup priority: HIGH (safe + often large).

## npm Cache
Location: `~/.npm` (Linux/Mac) or `%APPDATA%\npm-cache` (Windows).
Safety: Safe to delete. This caches previously-downloaded npm package tarballs so future `npm install` runs are faster. Clearing it (`npm cache clean --force`) does not remove any project's actual node_modules or affect any project's ability to build — it just means the next install re-downloads from the registry instead of a local cache hit. Recommended cleanup priority: HIGH.

## pip Cache
Location: `~/.cache/pip` (Linux/Mac) or `%LOCALAPPDATA%\pip\Cache` (Windows).
Safety: Safe to delete, same rationale as npm cache — it's a local wheel/package cache for faster reinstalls, not source of truth for any environment.

## Old Python Virtual Environments (venv / .venv folders)
Safety: CONDITIONAL. Safe to delete IF the associated project has a `requirements.txt`, `pyproject.toml`, or `Pipfile.lock` that can regenerate the exact same environment. UNSAFE to delete without checking first if no such manifest exists, since the exact package versions used may not be recoverable from memory. Detection heuristic: look for a sibling requirements.txt/pyproject.toml in the same project folder before recommending deletion; if absent, flag for manual review rather than auto-recommending deletion.

## Downloads Folder
Safety: NEVER auto-recommend for deletion. This is explicitly user-created content — installers, documents, media the user intentionally downloaded and may still need. At most, flag large old files (e.g. installers older than 90 days) individually for the user's own review, never as a bulk "safe to clean" category.

## Temporary Files (Windows %TEMP%, Linux /tmp)
Safety: MOSTLY safe. These are meant to be short-lived scratch files created by applications and the OS. Files actively in use by a running process can occasionally cause issues if force-deleted while the app is open (rare, usually just a harmless error from that app). Recommended approach: skip files currently locked/in-use rather than force-deleting, and prefer files older than a threshold (e.g. 7 days) as the safest subset.

## Application Cache / AppData (Windows %LOCALAPPDATA%, Mac ~/Library/Application Support)
Safety: CONDITIONAL, varies per application. Some apps store only regenerable cache here (safe), others store user settings, save data, or license state (unsafe to bulk-delete). Should not be recommended for bulk automated cleanup — requires app-by-app knowledge. Flag as "investigate individually" rather than blanket safe/unsafe.

## Old Project Folders / node_modules in inactive projects
Safety: node_modules folders are always regenerable via `npm install` given a package.json — safe to delete the node_modules subfolder specifically, keeping the rest of the project intact. The project folder itself (source code) should never be auto-deleted; only cache/dependency subfolders within it.

## Duplicate Files
Safety: CONDITIONAL. True byte-for-byte duplicates (verified by hash comparison, not just filename or size) are generally safe to deduplicate by keeping one copy. Files that merely have similar names or sizes are NOT confirmed duplicates and should not be treated as such without a hash check.

## Recycle Bin / Trash
Safety: Safe to empty if the user has confirmed they no longer need recently-deleted items — but by definition this permanently removes the last-resort recovery path for anything already deleted, so it should always be its own explicit approval step, never bundled silently into a general cleanup.

## System Restore Points / VSS Shadow Copies (Windows)
Safety: UNSAFE to auto-recommend for deletion. These are a system-level recovery mechanism; removing them eliminates the ability to roll back after a bad update or malware incident. Only relevant for advanced users making an informed trade-off, never a default cleanup suggestion.

## Docker images/containers/volumes (docker system prune)
Safety: CONDITIONAL. Unused/dangling images and stopped containers are generally safe to prune and regenerable by rebuilding. Volumes can contain persistent application data (e.g. a database's actual data files) and should be excluded from automatic pruning unless explicitly confirmed unused.

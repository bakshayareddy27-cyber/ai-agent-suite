# npm / pip / Python Package Manager Reference — Risk & Behavior Notes

## npm install (no args)
Installs all dependencies listed in package.json into node_modules. Low risk, standard operation. Can be slow and creates a large node_modules directory, but is fully regenerable and doesn't touch anything outside the project folder.

## npm install <package>
Adds a new package to node_modules and (by default in modern npm) to package.json dependencies. Low risk to the system, but installing packages from npm always carries **supply-chain risk**: a malicious or compromised package can run arbitrary code via install scripts (`postinstall` hooks) at install time, before you've even used the package. Worth checking package popularity/maintenance for unfamiliar packages, especially ones with typosquatted names close to popular packages.

## npm install -g <package>
Installs globally rather than into a project's node_modules, making the package's CLI available system-wide. Can require elevated permissions on some systems and can create version conflicts between projects that expect different global tool versions. Prefer `npx <package>` for one-off use, or per-project devDependencies, over global installs where possible.

## npm uninstall / npm prune
Removes packages from node_modules and package.json. Low risk, regenerable via `npm install` from a committed package-lock.json.

## rm -rf node_modules
Removes the entire dependency tree for a project. Fully safe and regenerable via `npm install`, since node_modules is never meant to be committed to version control (it's typically .gitignored). Common and appropriate when debugging dependency issues ("nuke and reinstall").

## pip install package==version
Installs a specific pinned version of a package into the currently active Python environment. Low risk on its own, but if run outside a virtual environment it installs into the **global/system Python**, which can conflict with system tools that depend on specific package versions (notably on Debian/Ubuntu, where system utilities use system Python). Pinning an old or incompatible version can also silently break other installed packages that share dependencies. Safer pattern: always work inside a virtual environment (`python -m venv venv`, then activate it) before running pip install.

## pip install --upgrade / pip install -U
Upgrades a package to the latest version compatible with other constraints. Can break code that relies on the older version's API (breaking changes between major versions). Check the changelog for packages with a history of breaking changes before blanket-upgrading in a working environment.

## pip uninstall
Removes a package from the current environment. Low risk; the environment can typically be rebuilt from a requirements.txt if something goes wrong.

## pip install with sudo (sudo pip install)
Installs into the system-wide Python environment with root privileges, which can conflict with or overwrite packages that the OS itself depends on (many Linux distros use Python for system scripts). Strongly discouraged; use a virtual environment instead, which requires no elevated privileges.

## Deleting a Python virtual environment (rm -rf venv/ or rm -rf .venv/)
Fully safe and regenerable as long as a requirements.txt (or pyproject.toml / poetry.lock) exists to reinstall dependencies from. If no such file exists and the environment was built up manually over time via ad-hoc `pip install` commands, deleting it loses the exact dependency list — running `pip freeze > requirements.txt` first is a good safety step before deleting.

## npm cache clean --force
Clears npm's local package cache to free disk space. Safe — the cache is purely a performance optimization for faster reinstalls; clearing it just means the next installs re-download packages from the registry instead of a local cache hit.

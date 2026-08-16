# Linux / Shell Command Reference — Risk & Behavior Notes

## rm -rf
Recursively (`-r`) and forcibly (`-f`, no confirmation prompts, ignores nonexistent files) deletes files and directories. There is no trash/recycle bin on most Linux shells — deletion is immediate and permanent, bypassing filesystem-level recovery in normal use. `rm -rf /` or `rm -rf /*` targeting the root or an unintended broad path (e.g. a mistyped `rm -rf ./ node_modules` with a stray space becoming `rm -rf ./` and `node_modules` as two separate targets) can destroy an entire system or unrelated directories. `rm -rf ./node_modules` scoped to a specific known directory is common and low-risk since node_modules is regenerable via `npm install`. Always risky when the target path contains a variable that could be empty (`rm -rf $VAR/*` deletes everything under `/` if `$VAR` is unset). Safer alternative: `rm -ri` for interactive confirmation, or move to a trash directory first (`trash-cli` package), or `ls` the target first to confirm scope.

## chmod
Changes file permissions. `chmod 777 <file>` grants read/write/execute to owner, group, and everyone — a security risk on any file reachable by other users or the network, especially scripts or config files, since it allows arbitrary modification/execution by any local user. `chmod +x script.sh` (adding execute permission) is low risk and commonly needed. Recursive `chmod -R 777 /` is severely destructive to system security and stability.

## chown
Changes file ownership. `chown -R user:group /path` recursively reassigns ownership; low risk on directories you control, but running it on system directories (`/etc`, `/usr`) can break permission expectations that system services rely on.

## sudo
Executes a command with root privileges. Any destructive command becomes system-wide when prefixed with `sudo` rather than scoped to the current user. `sudo rm -rf` removes the normal safeguard of permission errors that might otherwise stop an accidental deletion outside your home directory.

## dd
Low-level block copy tool, commonly used for disk imaging (`dd if=/dev/sdX of=backup.img`). If `if=` (input) and `of=` (output) are swapped, or the wrong device is targeted, `dd` will silently overwrite an entire disk with no confirmation and no undo — it operates below the filesystem, so there is no "recycle bin" and often no partial-recovery path. Always double and triple check device names with `lsblk` or `fdisk -l` before running.

## kill / kill -9
`kill <pid>` sends SIGTERM, a graceful shutdown request the process can catch and clean up after. `kill -9 <pid>` sends SIGKILL, which cannot be caught or ignored — the process is terminated immediately with no cleanup, which can leave temp files, locks, or database writes in an inconsistent state. Prefer plain `kill` first; escalate to `-9` only if the process doesn't respond.

## mv and cp with wildcards
`mv * /some/path` or `cp -r * /some/path` can silently overwrite existing files at the destination with no confirmation by default on most shells (unless `-i` for interactive mode is set). Low risk for data loss of the source (mv/cp don't delete unless overwritten), but can silently destroy files already present at the destination.

## curl | bash (or curl | sh)
Downloads a script from a URL and pipes it directly into a shell for execution without ever inspecting it first. This is a common install pattern (e.g. many CLI tool installers) but is inherently risky: the script runs with your full user permissions immediately, and you have no chance to review what it does, whether the source is compromised, or whether the URL could serve different content based on user-agent. Safer alternative: download the script first (`curl -o install.sh <url>`), read it, then run `bash install.sh`.

## systemctl / service management
`systemctl stop <service>` / `systemctl disable <service>` affects running system services; stopping a service like networking or SSH on a remote machine can lock you out of that machine with no local console access to recover.

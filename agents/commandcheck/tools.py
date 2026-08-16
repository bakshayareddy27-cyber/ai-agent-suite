"""
Tools available to the CommandCheck LangGraph agent.

These are genuine, deterministic tools (not LLM calls dressed up as
tools) that the graph nodes invoke. The LLM is used for the parts that
actually require language understanding (intent, effect explanation,
final verdict); pattern matching and lookups are done in real Python.
"""

import re
import shlex
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Tool 1: Command Parser
# ---------------------------------------------------------------------------

@dataclass
class ParsedCommand:
    raw: str
    tokens: list
    base_command: str
    subcommand: str | None
    flags: list
    targets: list
    shell_type: str  # git | npm | pip | linux | powershell | unknown


POWERSHELL_CMDLETS = {
    "remove-item", "set-executionpolicy", "invoke-webrequest", "invoke-expression",
    "stop-process", "format-volume", "clear-disk", "reg", "get-childitem",
    "new-item", "copy-item", "move-item",
}

FLAG_PATTERN = re.compile(r"^-{1,2}[A-Za-z].*")


def parse_command(command: str) -> ParsedCommand:
    """Real tokenization + classification of the command family."""
    command = command.strip()

    # Detect PowerShell piping to Invoke-Expression, a common install pattern
    lowered = command.lower()

    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. Fall back to naive split.
        tokens = command.split()

    if not tokens:
        return ParsedCommand(command, [], "", None, [], [], "unknown")

    base = tokens[0].lower()

    if base == "git":
        shell_type = "git"
    elif base == "npm":
        shell_type = "npm"
    elif base in ("pip", "pip3"):
        shell_type = "pip"
    elif base in POWERSHELL_CMDLETS or any(c in lowered for c in ["remove-item", "invoke-expression", "set-executionpolicy"]):
        shell_type = "powershell"
    elif base in ("rm", "chmod", "chown", "sudo", "dd", "kill", "mv", "cp", "curl", "systemctl"):
        shell_type = "linux"
    else:
        shell_type = "unknown"

    subcommand = tokens[1].lower() if len(tokens) > 1 and not FLAG_PATTERN.match(tokens[1]) else None
    flags = [t for t in tokens[1:] if FLAG_PATTERN.match(t)]
    targets = [t for t in tokens[1:] if not FLAG_PATTERN.match(t) and t != subcommand]

    return ParsedCommand(command, tokens, base, subcommand, flags, targets, shell_type)


# ---------------------------------------------------------------------------
# Tool 2: Deterministic Risk Heuristics
# ---------------------------------------------------------------------------

# Each rule: (regex, risk_level, reason_tag)
RISK_RULES = [
    (re.compile(r"rm\s+.*-[a-z]*r[a-z]*f|rm\s+.*-[a-z]*f[a-z]*r", re.I), "DESTRUCTIVE", "recursive_force_delete"),
    (re.compile(r"git\s+reset\s+.*--hard", re.I), "HIGH", "git_hard_reset"),
    (re.compile(r"git\s+push\s+.*--force(?!-with-lease)", re.I), "HIGH", "git_force_push"),
    (re.compile(r"git\s+clean\s+.*-[a-z]*f", re.I), "HIGH", "git_clean_force"),
    (re.compile(r"dd\s+if=", re.I), "DESTRUCTIVE", "raw_disk_write"),
    (re.compile(r"format-volume|clear-disk", re.I), "DESTRUCTIVE", "disk_format"),
    (re.compile(r"chmod\s+.*777", re.I), "HIGH", "insecure_permissions"),
    (re.compile(r"remove-item\s+.*-recurse\s+.*-force|remove-item\s+.*-force\s+.*-recurse", re.I), "HIGH", "ps_force_delete"),
    (re.compile(r"curl\s+.*\|\s*(sh|bash)|iwr\s+.*\|\s*iex|invoke-webrequest.*invoke-expression", re.I), "HIGH", "blind_remote_exec"),
    (re.compile(r"kill\s+-9|stop-process\s+.*-force", re.I), "MEDIUM", "force_kill"),
    (re.compile(r"sudo\s+rm", re.I), "DESTRUCTIVE", "sudo_delete"),
    (re.compile(r"set-executionpolicy\s+(unrestricted|bypass)", re.I), "HIGH", "disable_script_security"),
    (re.compile(r"reg\s+delete", re.I), "HIGH", "registry_delete"),
    (re.compile(r"git\s+branch\s+.*-D\b"), "MEDIUM", "force_branch_delete"),
    (re.compile(r"rm\s+.*-[a-z]*r[a-z]*f.*node_modules|rm\s+.*-[a-z]*f[a-z]*r.*node_modules", re.I), "LOW", "regenerable_deps"),
    (re.compile(r"npm\s+cache\s+clean", re.I), "LOW", "cache_clear"),
    (re.compile(r"pip\s+install(?!\s+--upgrade)", re.I), "LOW", "package_install"),
    (re.compile(r"npm\s+install\b", re.I), "LOW", "standard_install"),
    (re.compile(r"git\s+status|git\s+log|git\s+diff|git\s+fetch\b", re.I), "SAFE", "read_only"),
]


def assess_risk_heuristics(command: str):
    """
    Deterministic first-pass risk scan. Returns the highest-severity match.
    This runs BEFORE the LLM reasoning step so the agent has a grounded
    signal to reason over rather than guessing risk from scratch.
    """
    severity_order = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "DESTRUCTIVE": 4}
    matches = []
    for pattern, level, tag in RISK_RULES:
        if pattern.search(command):
            matches.append({"level": level, "tag": tag})

    if not matches:
        return {"level": "UNKNOWN", "tags": [], "matched_rules": 0}

    tags = [m["tag"] for m in matches]

    # Special case: a recursive-force-delete scoped specifically to
    # node_modules is a distinct, well-known LOW-risk pattern (regenerable
    # via `npm install`) even though it also matches the generic
    # "recursive force delete" rule. Prefer the more specific classification
    # as long as nothing else in the command raises independent concern
    # (sudo, wildcards, parent-directory traversal).
    if "regenerable_deps" in tags and not re.search(r"sudo|\*|\.\./|/\s*$", command, re.I):
        matches = [m for m in matches if m["tag"] != "recursive_force_delete"]
        tags = [m["tag"] for m in matches]

    top = max(matches, key=lambda m: severity_order[m["level"]])
    return {
        "level": top["level"],
        "tags": tags,
        "matched_rules": len(matches),
    }


# ---------------------------------------------------------------------------
# Tool 3: Safer Alternative Lookup
# ---------------------------------------------------------------------------

SAFER_ALTERNATIVES = {
    "git_hard_reset": "Run `git stash` first to save uncommitted work, or use `git reset --soft HEAD~1` if you only want to undo the commit, not the changes.",
    "git_force_push": "Use `git push --force-with-lease` instead — it aborts if the remote has commits you don't have locally, protecting teammates' work.",
    "git_clean_force": "Run `git clean -n` first (dry run) to see exactly what would be deleted before adding `-f`.",
    "recursive_force_delete": "Run `ls <target>` first to confirm the exact scope, or use `rm -ri` for per-file confirmation.",
    "raw_disk_write": "Run `lsblk` or `fdisk -l` to triple-check the target device name before running dd — a swapped if/of destroys the wrong disk.",
    "disk_format": "Confirm the exact disk/volume number with `Get-Disk` or Disk Management before formatting — this is irreversible.",
    "insecure_permissions": "Use the minimum permission needed, e.g. `chmod 755` (owner write, others read/execute) instead of `777`.",
    "ps_force_delete": "Run with `-WhatIf` first to preview what would be deleted, e.g. `Remove-Item -Recurse -Force <path> -WhatIf`.",
    "blind_remote_exec": "Download the script first (`curl -o install.sh <url>`), read it, then run it separately — never pipe an unread remote script directly into a shell.",
    "force_kill": "Try a plain `kill <pid>` (or `Stop-Process` without -Force) first to allow graceful shutdown before escalating to force.",
    "sudo_delete": "Double-check the target path without sudo first; consider whether the operation genuinely needs root at all.",
    "disable_script_security": "Use `Set-ExecutionPolicy RemoteSigned` instead — it still allows local scripts while requiring downloaded scripts to be signed.",
    "registry_delete": "Export the key first as backup: `reg export <key> backup.reg` before deleting.",
    "force_branch_delete": "Merge the branch first if possible, or confirm with `git log <branch>` that you don't need its unique commits before force-deleting.",
}


def lookup_safer_alternative(tags: list):
    for tag in tags:
        if tag in SAFER_ALTERNATIVES:
            return SAFER_ALTERNATIVES[tag]
    return None


# ---------------------------------------------------------------------------
# Tool 4: Verification Command Suggestion
# ---------------------------------------------------------------------------

VERIFICATION_COMMANDS = {
    "git": "git status && git log --oneline -5",
    "npm": "npm list --depth=0",
    "pip": "pip show <package_name>",
    "linux": "ls -la <target_path>",
    "powershell": "Get-ChildItem <target_path>",
}


def suggest_verification(shell_type: str):
    return VERIFICATION_COMMANDS.get(shell_type)

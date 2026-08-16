# PowerShell Command Reference — Risk & Behavior Notes

## Remove-Item (rm, del, ri, erase are aliases)
`Remove-Item -Recurse -Force <path>` deletes files/folders recursively without confirmation prompts, bypassing the Recycle Bin — deletion is permanent, unlike deleting via File Explorer which normally goes to Recycle Bin. `-WhatIf` flag previews what would be deleted without deleting anything; a safe way to check scope first. `-Confirm` forces a per-item confirmation prompt.

## Set-ExecutionPolicy
Controls whether PowerShell scripts (.ps1 files) are allowed to run on the system. `Set-ExecutionPolicy Unrestricted` or `Bypass` (especially with `-Scope CurrentUser` or system-wide) removes a security guardrail intended to prevent unsigned/untrusted scripts from executing silently, e.g. via malicious downloads or phishing. `RemoteSigned` is a common middle-ground default that allows locally-created scripts but requires internet-downloaded scripts to be signed.

## Invoke-WebRequest | Invoke-Expression (iwr ... | iex)
Downloads content from a URL and immediately executes it as PowerShell code, without any opportunity to inspect it first — the PowerShell equivalent of `curl | bash`. Commonly seen in one-line installer commands. Carries the same blind-execution risk: the script runs with your current permissions immediately, and the served content could differ from what a human reviewer sees if fetched via browser.

## Stop-Process / Stop-Process -Force
`Stop-Process -Id <pid>` or `-Name <name>` terminates a process. `-Force` skips confirmation and terminates even processes that would normally prompt. Force-killing a process skips its normal shutdown/cleanup routine, which can leave open files or in-progress writes in an inconsistent state, similar to `kill -9` on Linux.

## Format-Volume / Clear-Disk
Formats or wipes a disk volume, destroying all data on it. Extremely destructive and irreversible through normal means. Always requires explicit target drive letter/disk number confirmation — a wrong target here means permanent data loss with no undo.

## Remove-Item -Recurse -Force on system paths (e.g. C:\Windows, C:\Program Files)
Deleting or modifying core OS directories can render Windows unbootable or break installed applications. Any recursive-force delete targeting a path outside a project/user-owned folder deserves extra scrutiny.

## reg delete (Registry edits)
Deletes a Windows Registry key or value. The registry controls core OS and application configuration; deleting the wrong key can break installed software, user profiles, or in severe cases prevent Windows from booting. No confirmation by default without extra flags, and no straightforward undo unless a registry backup or System Restore point exists beforehand.

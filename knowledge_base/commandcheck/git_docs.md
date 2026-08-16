# Git Command Reference — Risk & Behavior Notes

## git reset
`git reset --soft <ref>` moves the branch pointer only; staged changes and working directory are untouched. Safe.
`git reset --mixed <ref>` (default) moves the branch pointer and unstages changes, but keeps them in the working directory. Generally safe, changes are not lost.
`git reset --hard <ref>` moves the branch pointer AND overwrites the working directory AND the index to match `<ref>`. Any uncommitted changes and any commits after `<ref>` that are not referenced elsewhere are permanently discarded from the working tree. This is destructive to uncommitted work. Commits themselves are usually recoverable for ~30-90 days via `git reflog` and `git reset --hard <reflog-entry>`, but uncommitted working directory changes are NOT recoverable — git never tracked them, so there is no object to restore. Safer alternative before running: `git stash` to save uncommitted work, or `git diff > backup.patch` to snapshot it. Verification after running: `git status` and `git log --oneline -5`.

## git clean
`git clean -n` (dry run) lists untracked files that would be removed without deleting anything. Always safe.
`git clean -f` deletes untracked files permanently, no trash/recycle bin involved. Combined with `-d` it also removes untracked directories. `-x` additionally removes files ignored by .gitignore (e.g. build artifacts, .env files if gitignored). This is irreversible — deleted files are not tracked by git and cannot be recovered from git history. Always run `git clean -n` first to preview.

## git push --force
Overwrites the remote branch history with your local history, discarding any commits on the remote that aren't in your local branch. This can destroy teammates' work if they've pushed commits you don't have locally. `git push --force-with-lease` is a safer alternative: it fails if the remote has commits you haven't fetched, preventing accidental overwrites of others' work.

## git checkout -- <file> / git restore <file>
Discards uncommitted changes to a specific tracked file, replacing it with the last committed version. Destructive to local edits on that file only, does not affect other files or commit history. No safer alternative needed if the intent is genuinely to discard changes; otherwise `git stash` first.

## git rebase
Rewrites commit history by replaying commits onto a new base. Safe on local/private branches. On shared branches that others have already pulled, rebasing and force-pushing rewrites history they've built on, causing conflicts and confusion. Interactive rebase (`git rebase -i`) can also squash, reorder, or drop commits — dropping a commit discards its changes unless recovered via reflog.

## git branch -D
Force-deletes a branch even if it has unmerged commits. Regular `git branch -d` refuses to delete unmerged branches as a safety check; `-D` bypasses that check. Commits on the deleted branch become unreachable from any branch ref but remain recoverable via `git reflog` for a limited time (subject to git gc).

## git add -A / git commit --amend
`git add -A` stages all changes including deletions; generally safe, just broad in scope — worth checking `git status` first to avoid staging unintended files (e.g. secrets, build output).
`git commit --amend` replaces the most recent commit with a new one (message and/or content). If that commit has already been pushed and others have pulled it, amending and force-pushing rewrites shared history.

## git fetch vs git pull
`git fetch` downloads remote changes without merging them into your working branch — always safe, non-destructive.
`git pull` = `git fetch` + `git merge` (or rebase if configured). Can create merge commits or conflicts but does not silently discard local commits; uncommitted working directory changes can conflict and block the pull, which git will warn about rather than overwrite silently.

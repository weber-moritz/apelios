# Git Repository Cleanup Guide (Open Source Prep)

Complete workflow to sanitize a Git repository before making it public. Remove sensitive data, embarrassing notes, prototype code, or anything you don't want in the public history.

---

## Prerequisites

- Install [`git-filter-repo`](https://github.com/newren/git-filter-repo):
  ```bash
  pip install git-filter-repo
  ```
- Have write access to the repository
- **Read this entire guide before executing anything**

---

## Phase 1: Safety Backup (DO NOT SKIP)

Create a **full local backup** of your repository including `.git` folder:

```bash
# Navigate to parent directory of your repo
cd /path/to/parent

# Create a complete backup (includes all branches, tags, history)
cp -r your-repo your-repo-backup-$(date +%Y%m%d)

# Verify the backup
ls -la your-repo-backup-*/.git
```

**Keep this backup until you confirm the cleaned repo is perfect.**

---

## Phase 2: Find Problematic Content

### 2.1 Find files by name

List all files ever committed, sorted and unique:
```bash
cd your-repo
git log --all --name-only --format="" | sort -u
```

Look for: `notes.txt`, `todo.md`, `prof_*.*`, `private.*`, `secrets.*`, etc.

### 2.2 Find by content

Search all commit history for specific text (case insensitive):
```bash
# Search for a name
git log --all -i -S "ProfName" -p

# Search for email
git log --all -i -S "email@example.com" -p

# Search for password/secret patterns
git log --all -i -S "password" -p
git log --all -i -S "api_key" -p
git log --all -i -S "secret" -p
```

### 2.3 List all large files

Find large files that might contain sensitive data:
```bash
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '/^blob/ {print substr($0,6)}' | sort --numeric-sort --key=2 | tail -n 20
```

### 2.4 Document what you found

Create a list of what needs removal:
```
Files to remove completely:
- path/to/file1.txt
- path/to/file2.md

Strings to remove from file contents:
- "MySecretPassword"
- "api_key=abc123"

Branches to verify:
- old-prototype-branch
- experimental-feature
```

---

## Phase 3: Clean History

### 3.1 Remove entire files from history

For each file that should never have existed:
```bash
# Remove a single file from all history
git filter-repo --force --invert-paths --path path/to/file.txt

# Remove multiple files at once
git filter-repo --force --invert-paths --path path/to/file1.txt --path path/to/file2.md
```

### 3.2 Remove strings from file contents

For sensitive strings that appear in files you want to keep:
```bash
# Replace text in all files across all commits
git filter-repo --force --replace-text <(echo "MySecretPassword==>REDACTED")

# Multiple replacements from a file
echo "old-text==>new-text" > replacements.txt
echo "secret-key==>REDACTED" >> replacements.txt
git filter-repo --force --replace-text replacements.txt
```

### 3.3 Remove specific commits

If entire commits are problematic:
```bash
# Find commit hash
git log --oneline --all

# Remove a specific commit
git filter-repo --force --invert-paths --path-glob '*' --ref HEAD~5..HEAD~4
```

### 3.4 Clean up branches and tags

Remove branches you don't want to publish:
```bash
# Delete local branches
git branch -D old-prototype-branch
git branch -D experimental-feature

# Delete remote branches (after pushing)
git push origin --delete old-prototype-branch
```

---

## Phase 4: Verify Cleanup

### 4.1 Check history again

Re-run your search commands from Phase 2:
```bash
git log --all --name-only --format="" | sort -u
git log --all -i -S "ProfName" -p
git log --all -i -S "password" -p
```

### 4.2 Check file sizes

Verify large files were removed:
```bash
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '/^blob/ {print substr($0,6)}' | sort --numeric-sort --key=2 | tail -n 20
```

---

## Phase 5: Decide on History Strategy

### Option A: Keep Full History (Recommended if clean)

If Phase 4 shows no sensitive data remains:
```bash
# Force push cleaned history to ALL remote branches
git push origin --all --force
git push origin --tags --force

# Anyone who cloned before must re-clone
```

### Option B: Squash Early History (Fresh Start)

If early commits are messy prototype code:

```bash
# Create a new orphan branch from current state
git checkout --orphan new-master

# Add all current files
git add -A
git commit -m "Initial commit: Clean project state"

# Create new main branch
git branch -m new-master main

# Force push this as the new history
git push origin main --force

# Delete old branches on remote
git push origin --delete old-master
```

**Warning**: This completely rewrites history. All contributors must re-clone.

---

## Phase 6: Final Checks

### 6.1 Clone fresh and verify

```bash
cd /tmp
rm -rf your-repo-verify
git clone https://github.com/your-account/your-repo.git your-repo-verify
cd your-repo-verify

# Run your searches again
git log --all --name-only --format="" | sort -u
git log --all -i -S "sensitive-term" -p
```

### 6.2 Verify GitHub/GitLab

- Check the repository is private until you're sure
- Verify no sensitive data appears in GitHub's code search
- Check GitHub's "Insights" > "Code frequency" and "Contributors" look correct

---

## Important Notes

### Force Push Warning

- **Force pushing rewrites history**
- Anyone who cloned before must **delete their local clone and re-clone**
- Communicate this clearly to all collaborators

### What `filter-repo` Doesn't Touch

- **Reflog**: Local reflog entries remain (not pushed to remote)
- **Working directory**: Uncommitted files are untouched
- **Stashes**: Git stashes are not affected

### Large File Considerations

If you had large binary files:
- Consider using `git lfs` for files >100MB
- GitHub has a 100MB file limit

---

## Recovery (If Something Goes Wrong)

If the cleanup broke something:

```bash
# From your backup (created in Phase 1)
cd /path/to/parent
cp -r your-repo-backup-*/.git your-repo/
cd your-repo
git reset --hard HEAD
```

---

## Quick Start (TL;DR)

For most cases, this is sufficient:

```bash
# 1. Backup
cp -r your-repo your-repo-backup

# 2. Remove sensitive files
git filter-repo --force --invert-paths --path path/to/sensitive/file

# 3. Remove sensitive strings
git filter-repo --force --replace-text <(echo "sensitive-text==>REDACTED")

# 4. Verify
git log --all -i -S "sensitive-text" -p

# 5. Push (if clean)
git push origin --all --force
git push origin --tags --force
```

---

*Last Updated: 2026-07-15*

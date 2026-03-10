---
description: Automatically commit and push changes to main branch for Plan_convert_SQL project
version: 2.0
---

# Auto Commit Workflow v2.0

## Overview
This workflow automatically commits and pushes code changes to the main branch with pull-before-push and conflict resolution capabilities.

## Steps

### Phase 0: Sync with Remote (PULL FIRST - REQUIRED)
- Run `git fetch origin` to fetch latest remote changes
- Run `git rev-list --count HEAD..origin/main` to check if local is behind remote
- If count > 0 (local is behind): Run `git pull --rebase origin main` to get latest commits
- Check git status after pull
- If conflicts detected → Go to Phase 1: Conflict Resolution
- If no conflicts → Continue to Phase 2

### Phase 1: Conflict Detection
- Run `git status --short` to check for conflicts
- Look for conflict indicators:
  - `UU` = both modified (conflict)
  - `DU` = deleted by us (local deleted, remote modified)
  - `UD` = deleted by them (remote deleted, local modified)
- Run `git diff --name-only --diff-filter=U` to list conflicted files
- If no conflicted files → Continue to Phase 2

### Phase 1.5: Conflict Resolution (Interactive)
If conflicts detected, present options to user:

```
⚠️  CONFLICT DETECTED!

Conflicting files:
  - main_qt.py (both modified)
  - sql_query.py (both modified)

Resolution Options:

  [1] Keep Local Changes (Overwrite Remote)
      → Giữ thay đổi local, ghi đè remote
      
  [2] Keep Remote Changes (Accept Theirs)
      → Chấp nhận thay đổi remote, bỏ local
      
  [3] Merge Both (Manual Resolution)
      → Giữ cả hai, đánh dấu conflict để sửa thủ công
      
  [4] Use Ours (Keep Local Version)
      → Giữ phiên bản local cho từng file
      
  [5] Use Theirs (Keep Remote Version)
      → Giữ phiên bản remote cho từng file
      
  [6] Abort & Reset
      → Hủy bỏ, quay lại trạng thái trước pull
      
  [7] Abort & Continue Local Changes
      → Hủy pull, giữ local changes như chưa sync

👉 Chọn option [1-7]: 
```

#### Option 1: Keep Local Changes (Overwrite Remote)
Commands:
```
git checkout --ours {file1} {file2} ...
git add {file1} {file2} ...
git commit -m "Resolve conflicts: keep local changes"
```
Result: Local changes override remote changes

#### Option 2: Keep Remote Changes (Accept Theirs)
Commands:
```
git checkout --theirs {file1} {file2} ...
git add {file1} {file2} ...
git commit -m "Resolve conflicts: accept remote changes"
```
Result: Remote changes override local changes

#### Option 3: Merge Both (Manual Resolution)
Commands:
```
# Open each conflicted file and resolve manually
git add {file1} {file2} ...
git commit -m "Resolve conflicts: manual merge"
```
Result: User manually resolves conflicts in each file

#### Option 4: Use Ours (Keep Local Version Per File)
Commands:
```
# For each conflicted file:
git checkout --ours {file}
git add {file}
git commit -m "Resolve conflicts: use ours for {file}"
```
Result: Keep local version for specified files

#### Option 5: Use Theirs (Keep Remote Version Per File)
Commands:
```
# For each conflicted file:
git checkout --theirs {file}
git add {file}
git commit -m "Resolve conflicts: use theirs for {file}"
```
Result: Keep remote version for specified files

#### Option 6: Abort & Reset
Commands:
```
git rebase --abort
git status
```
Result: Return to state before pull, local changes preserved

#### Option 7: Abort & Continue Local Changes
Commands:
```
git reset --hard HEAD~1
git status
```
Result: Cancel pull, keep local changes unsynced

### Phase 2: Stage Changes
- Run `git status` to see modified files
- If no arguments provided: Run `git add -A` to stage all changes
- If file paths provided: Run `git add -A {file_paths}` to stage specified files
- Verify staged changes with `git diff --staged`

### Phase 3: Create Commit
- Generate appropriate commit message based on changes
- Include list of committed files in commit message
- Run `git commit -m "{commit_message}"`
- Verify commit was created successfully with `git log -1`

### Phase 4: Push to Remote
- Run `git push -u origin main` to push to remote branch
- Verify push succeeded
- Confirm remote branch is updated
- Show push result and commit hash

## Usage
```
/commit_workflow
/commit_workflow main_qt.py
/commit_workflow main_qt.py sql_query.py execution_sql.py
/commit_workflow --message "Add new SQL parsing feature"
```

## Options
- **No arguments**: Run `git add -A` to commit all changes
- **File paths**: Run `git add -A {file_paths}` to commit specified files only
- **--message**: Custom commit message (default: "Auto commit changes")

## Git Commands Used

### Pull & Sync Commands
```bash
# Fetch latest remote changes
git fetch origin

# Check if local is behind
git rev-list --count HEAD..origin/main

# Pull with rebase (keep clean history)
git pull --rebase origin main

# Pull with merge
git pull origin main

# Abort rebase
git rebase --abort

# Reset to previous commit
git reset --hard HEAD~1
```

### Conflict Detection Commands
```bash
# Check git status for conflicts
git status --short

# List conflicted files
git diff --name-only --diff-filter=U

# Show conflicts in a file
git diff {file}

# Show conflict markers
grep -r "<<<<<<< HEAD" .
```

### Conflict Resolution Commands
```bash
# Accept local version (ours)
git checkout --ours {file}

# Accept remote version (theirs)
git checkout --theirs {file}

# Stage resolved file
git add {file}

# Commit merge
git commit -m "Resolve conflicts"
```

### Stage & Commit Commands
```bash
# Stage all changes
git add -A

# Stage specific files
git add -A file1.py file2.py

# Commit changes
git commit -m "Your commit message"

# View last commit
git log -1

# View commit details
git show HEAD
```

### Push Commands
```bash
# Push to main branch
git push -u origin main

# Force push (dangerous - use carefully)
git push --force origin main

# Push with lease (safer than force)
git push --force-with-lease origin main
```

## Workflow Flow Diagram

```
START
  ↓
Phase 0: Sync with Remote
  ↓
Pull latest commits (git fetch + git pull --rebase)
  ↓
Any conflicts?
  ├─ YES → Phase 1: Conflict Detection
  │         ↓
  │         Show conflicted files
  │         ↓
  │         Present resolution options [1-7]
  │         ↓
  │         User selects option
  │         ↓
  │         Apply resolution
  │         ↓
  │         Go to Phase 2
  │
  └─ NO → Phase 2: Stage Changes
          ↓
          Phase 3: Create Commit
          ↓
          Phase 4: Push to Remote
          ↓
        END
```

## Output
- List of committed files
- Commit hash
- Push status
- Remote branch URL
- Conflict resolution details (if applicable)

## Error Handling

### Pull Fails
- Show error message from git
- Check network connectivity
- Verify remote URL: `git remote -v`
- Option to retry or abort

### Conflicts Not Resolved
- Cannot push with unresolved conflicts
- Require user to resolve conflicts manually
- Provide guidance on conflict resolution

### Push Fails
- Check if remote has new commits
- Show error message
- Option to pull again and retry
- Option to abort with local changes preserved

## Examples

### Example 1: Normal Commit (No Conflicts)
```
Phase 0: Sync with Remote
  → git fetch origin
  → Already up to date

Phase 2: Stage Changes
  → git add -A main_qt.py sql_query.py

Phase 3: Create Commit
  → git commit -m "Update SQL parser"

Phase 4: Push to Remote
  → git push -u origin main
  → Success! abc123def
```

### Example 2: Conflict Detected (Option 1)
```
Phase 0: Sync with Remote
  → git pull --rebase origin main
  → CONFLICT in main_qt.py

Phase 1: Conflict Resolution
  → Option 1: Keep local changes
  → git checkout --ours main_qt.py
  → git add main_qt.py
  → git commit -m "Resolve conflicts: keep local"

Phase 2-4: Continue normal commit flow
```

### Example 3: Conflict Detected (Option 6 - Abort)
```
Phase 0: Sync with Remote
  → git pull --rebase origin main
  → CONFLICT in sql_query.py

Phase 1: Conflict Resolution
  → Option 6: Abort & Reset
  → git rebase --abort
  → Local changes preserved
  → Workflow aborted
```

## Best Practices

1. **Always pull before push** - Ensure you have latest changes
2. **Review conflicts carefully** - Don't auto-resolve important conflicts
3. **Use rebase over merge** - Keeps git history cleaner
4. **Test after resolution** - Verify resolved code works correctly
5. **Commit atomic changes** - Small, focused commits are easier to resolve
6. **Backup important work** - Use `git stash` if unsure about conflicts

## Troubleshooting

### Stuck in Rebase
```bash
# Check rebase status
git status

# If in rebase, abort
git rebase --abort

# Or continue rebase
git rebase --continue
```

### Merge vs Rebase Conflicts
```bash
# Rebase conflicts (one by one)
# Resolve first conflict
git add {file}
git rebase --continue

# Merge conflicts (all at once)
# Resolve all conflicts
git add {files}
git commit
```

### Lost Changes After Conflict Resolution
```bash
# Use reflog to find lost commits
git reflog

# Reset to previous state
git reset --hard {commit_hash}
```

## Notes
- Workflow always pulls latest commits before pushing
- User must resolve conflicts interactively
- No automatic conflict resolution to prevent data loss
- All git commands are standard and reversible
- Detailed logging helps troubleshoot issues

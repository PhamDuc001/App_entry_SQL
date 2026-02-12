---
description: Automatically commit and push changes to main branch for Plan_convert_SQL project
---

# Auto Commit Workflow

## Overview
This workflow automatically commits and pushes code changes to the main branch using standard git commands.

## Steps

### Phase 1: Stage Changes
- Run `git status` to see modified files
- If no arguments provided: run `git add -A` to stage all changes
- If file paths provided: run `git add -A {file_paths}` to stage specified files
- Verify staged changes with `git diff --staged`

### Phase 2: Create Commit
- Generate appropriate commit message based on changes
- Run `git commit -m "{commit_message}"`
- Include list of committed files in commit message
- Verify commit was created successfully

### Phase 3: Push to Remote
- Run `git push -u origin main` to push to remote branch
- Handle merge conflicts if any
- Verify push succeeded
- Confirm remote branch is updated

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
```bash
# Stage all changes
git add -A

# Stage specific files
git add -A file1.py file2.py

# Commit changes
git commit -m "Your commit message"

# Push to main branch
git push -u origin main
```

## Output
- List of committed files
- Commit hash
- Push status
- Remote branch URL

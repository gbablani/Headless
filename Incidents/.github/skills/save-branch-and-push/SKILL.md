---
name: save-branch-and-push
description: |
  Git branch creation and push skill for saving local changes to a new remote branch. Automatically activated when users request any of these tasks:
  - Save changes to a new branch ("save my changes", "create a branch with my changes", "push my changes")
  - Create a fix branch ("create a fix branch", "branch and push")
  - Push local work to remote ("push to remote", "save work to remote branch")
---

# Save Changes to New Branch and Push

This skill commits all local changes to a new branch named `dev/flakytest/fix<short GUID>` and pushes the branch to the remote repository.

## Steps

### 1. Verify Uncommitted Changes Exist

Check that there are actual changes to save before proceeding.

**Command:**
```powershell
git status --porcelain
```

**Execution Context:**
- Navigate to the root directory of the repository
- Execute in a `pwsh` (PowerShell Core) terminal

**Expected Output:**
- Non-empty output indicates changes exist; proceed to Step 2.
- Empty output means there are no changes to save; inform the user and stop.

**Troubleshooting:**

| Error | Solution |
|-------|----------|
| "not a git repository" | Verify you are inside the repository root directory |

### 2. Generate a Short GUID for the Branch Name

Generate a short GUID to create a unique branch name.

**Command:**
```powershell
$shortGuid = [System.Guid]::NewGuid().ToString("N").Substring(0, 8)
$username = $env:USERNAME
$branchName = "dev/$username/fix$shortGuid"
Write-Output "Branch name: $branchName"
```

**Expected Output:**
```
Branch name: dev/baisu/fix1a2b3c4d
```

**Details:**
- Uses the first 8 hex characters of a new GUID for uniqueness.
- The branch name format is `dev/<username>/fix<8-char-hex>`.
- user lowercase to avoid issues with naming conventions.

### 3. Create and Switch to the New Branch

Create a new local branch from the current HEAD and switch to it.

**Command:**
```powershell
git checkout -b $branchName
```

**Verification:**
Confirm the active branch matches the new branch name:
```powershell
git rev-parse --abbrev-ref HEAD
```

**Troubleshooting:**

| Error | Solution |
|-------|----------|
| "fatal: A branch named '<branch>' already exists" | Regenerate the GUID (re-run Step 2) and retry |
| "error: Your local changes to the following files would be overwritten" | Stage changes first with `git add -A` before switching |

### 4. Stage All Changes

Stage all modified, added, and deleted files for commit.

**Command:**
```powershell
git add -A
```

**Verification:**
Confirm files are staged:
```powershell
git diff --cached --stat
```

The output should list the files staged for commit.

### 5. Commit the Changes

Commit the staged changes with a descriptive message.

**Command:**
```powershell
git commit -m "Fix flaky test - saved changes to $branchName"
```

**Troubleshooting:**

| Error | Solution |
|-------|----------|
| "nothing to commit, working tree clean" | All changes were already committed; proceed to Step 6 |
| Author identity unknown | Run `git config user.email "you@example.com"` and `git config user.name "Your Name"` first |

### 6. Push the Branch to Remote

Push the new branch to the `origin` remote.

**Command:**
```powershell
git push origin $branchName
```

**Expected Output:**
```
 * [new branch]      dev/flakytest/fix1a2b3c4d -> dev/flakytest/fix1a2b3c4d
```

**Verification:**
Confirm the remote tracking branch is set:
```powershell
git branch -vv
```

The current branch should show `[origin/dev/flakytest/fix...]`.

**Troubleshooting:**

| Error | Solution |
|-------|----------|
| "fatal: 'origin' does not appear to be a git repository" | Run `git remote -v` to check remotes and use the correct remote name |
| Permission denied (publickey) | Verify SSH keys or switch to HTTPS authentication |
| "error: failed to push some refs" | Run `git pull --rebase origin <default-branch>` to incorporate upstream changes, then retry push |

### 7. Report Success

After a successful push, report the branch name to the user so they can reference it for pull requests or further work.

**Example Response:**
```
Changes saved and pushed successfully!
Branch: dev/flakytest/fix1a2b3c4d
Remote: origin/dev/flakytest/fix1a2b3c4d
```

## Rules

- **Always verify changes exist** before creating a branch to avoid empty commits.
- **Do not modify the default branch** - always create a new branch for changes.
- **Use the exact branch naming convention** - `dev/flakytest/fix<8-char-hex-GUID>`.
- **Do not force-push** - use regular `git push` only.
- **Report failures clearly** - if any step fails, report the error and stop.
- **Preserve the user's working state** - do not discard or reset any changes during this workflow.

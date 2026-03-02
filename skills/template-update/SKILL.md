---
name: template-update
description: Check for and pull updates from the upstream copilot-cli-starter repo. Use when asked to check for starter updates, pull starter updates, sync from starter, or see what's new from the copilot-cli-starter template source. Do NOT use for general template or workspace questions.
---

# Template Update — Pull from Upstream Starter

Checks the upstream `copilot-cli-starter` repo for new or updated content and lets you selectively incorporate changes into your local setup. This skill is specifically for pulling updates from the **copilot-cli-starter** source repo — not for general template management.

## Prerequisites

- Your repo must be a **fork** of the upstream template (or have an `upstream` remote configured)
- Git must be available in the terminal

**Note:** The skill auto-detects and configures everything. The user does NOT need to manually set up remotes or navigate to the repo directory — the skill handles it.

## Finding the Repo

1. **First:** Check `~/.copilot/.copilot-sync/sync-state.json` for a `repo_path` field
2. **Then:** Check if `cwd` is inside a git repo that has `init.ps1` and `personas/` directory
3. **Fallback:** Search common locations:
   - `~/copilot-cli-starter`
   - `~/GitHubProjects/copilot-cli-starter`
4. **If not found:** Ask the user for the repo path — do NOT assume a location
5. `cd` to the repo before proceeding

## Setting Up Upstream

Before checking for updates, verify the `upstream` remote exists:

```bash
git remote -v | grep upstream
```

If not configured, **auto-configure it** — don't ask the user to do it manually:
```bash
git remote add upstream https://github.com/jimbanach/copilot-cli-starter.git
```

Confirm to the user: "Added upstream remote pointing to the template source."

## Workflow: Check for Starter Updates

**Triggers:** "Check for starter updates", "Pull starter updates", "Sync from starter"

**Steps:**

1. Find the copilot-cli-starter repo (check cwd, then `~/copilot-cli-starter`)
2. `cd` to the repo directory

3. **To incorporate updates** (fetch + merge + deploy in one step), run this script:

   ```powershell
   powershell -File skills/template-update/update-starter.ps1
   ```

   The script handles everything:
   - Verifies/adds upstream remote
   - Fetches latest from upstream
   - Shows what's new (commits + changed files)
   - Merges upstream/main
   - **Deploys changed files directly to `~/.copilot/`**
   - Shows a deployment summary

4. **To preview without changes** (dry run):
   ```powershell
   powershell -File skills/template-update/update-starter.ps1 -DryRun
   ```

5. **If the user wants to review diffs first**, show them before running the script:
   ```bash
   git fetch upstream
   git --no-pager diff HEAD..upstream/main
   ```
   Then present structured options — do NOT ask freeform:
   ```
   [1] Incorporate — run the update script to merge and deploy
   [2] Skip — don't merge, check again later
   ```

## Handling Merge Conflicts

If the update script reports a merge conflict:

1. Show the conflicted files
2. For each conflict, display both versions (yours vs upstream)
3. Ask the user which to keep, or offer to open in editor
4. After resolution, complete the merge commit
5. Re-run the deploy portion of the script

## Important Notes

- The `update-starter.ps1` script is the **single source of truth** for the update workflow. Always use it instead of running git commands separately.
- Your local customizations (personas you've edited, skills you've added) are preserved — only upstream additions and changes to files you haven't modified are auto-incorporated.
- Files under `base/` (templates, instance rules) are NOT auto-deployed because they require variable resolution — the script will tell the user to run `init.ps1` if those changed.

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

1. Check if `cwd` is inside a git repo that has `init.ps1` and `personas/` directory
2. If not, search common locations: `~/copilot-cli-starter`, `~/GitHubProjects/copilot-cli-starter`
3. If not found, ask the user for the repo path
4. `cd` to the repo before proceeding

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

## Workflow: Check for Template Updates

**Triggers:** "Check for template updates", "Are there new features from the template?", "Pull upstream changes"

**Steps:**

1. Verify `upstream` remote exists. If not, ask the user to add it.

2. Fetch latest from upstream:
   ```bash
   git fetch upstream
   ```

3. Compare local against upstream/main. Show what's changed:
   ```bash
   git --no-pager log HEAD..upstream/main --oneline
   ```

4. If there are new commits, present a summary:

```
📊 Template Update — What's New
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upstream has 3 new commits since your last pull:

📝 Changes:
   • New skill: config-sync (compare, sanitize, sync-state scripts)
   • Updated: personas/architect-marketer/AGENTS.md (generalized)
   • Updated: README.md (added prerequisites section)

What would you like to do?
  [1] Review changes — see diffs before deciding
  [2] Incorporate all — merge upstream into your branch
  [3] Skip for now — don't merge, check again later
```

5. If "Review changes": For each changed file, show the diff and ask:
   - **Incorporate** — accept the upstream change
   - **Skip** — keep your local version
   - **Show diff** — see the detailed line-by-line diff

6. If "Incorporate all" or selective incorporations:
   - Create a backup branch before merging: `git checkout -b backup-before-update`
   - Switch back and merge: `git merge upstream/main --no-commit`
   - If conflicts exist, show them and help resolve
   - Commit with a descriptive message

7. After merging, re-run `init.ps1` to deploy any new content to `~/.copilot/`

## Handling Merge Conflicts

If upstream changes conflict with your local customizations:

1. Show the conflicted files
2. For each conflict, display both versions (yours vs upstream)
3. Ask the user which to keep, or offer to open in editor
4. After resolution, complete the merge commit

## Important Notes

- This skill never force-merges. Every change requires user approval.
- Your local customizations (personas you've edited, skills you've added) are preserved — only upstream additions and changes to files you haven't modified are auto-incorporated.
- Always create a backup branch before merging so you can revert if needed.
- After incorporating updates, run `init.ps1` to deploy changes to your local `~/.copilot/`.

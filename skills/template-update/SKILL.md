---
name: template-update
description: Check for updates from the upstream copilot-cli-starter template. Use when asked to check for template updates, pull upstream changes, or see what's new from the template maintainer.
---

# Template Update

Checks the upstream `copilot-cli-starter` template for new or updated content and lets you selectively incorporate changes into your local setup.

## Prerequisites

- Your repo must be a **fork** of the upstream template (or have an `upstream` remote configured)
- Git must be available in the terminal

## Setting Up Upstream

If the `upstream` remote isn't configured yet, set it up:

```bash
git remote add upstream https://github.com/jimbanach/copilot-cli-starter.git
```

Verify with:
```bash
git remote -v
# Should show both 'origin' (your fork) and 'upstream' (template source)
```

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

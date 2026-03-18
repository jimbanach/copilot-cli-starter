---
name: config-sync
description: Review, compare, and sync Copilot CLI configuration between machines and the config repo. Use when asked to check for updates, share setup, sync status, promote changes to universal, or publish a template for peers.
---

# Config Sync

Manages bidirectional sync between the local `~/.copilot/` setup and the `copilot-cli-config` repo. Keeps work and personal machines in sync while maintaining instance-specific boundaries.

## Prerequisites

- The `copilot-cli-config` repo must be cloned locally
- The repo path is stored in `instance-config.json` at the repo root (created by `init.ps1`)
- Git must be available in the terminal

## Finding the Repo

1. **First:** Check `~/.copilot/.copilot-sync/sync-state.json` for the `repo_path` field — this is the most reliable source since it's set by init.ps1
2. **Fallback:** Search common locations for `instance-config.json`:
   - `~/copilot-cli-config/`
   - `~/GitHubProjects/copilot-cli-config/`
   - Current working directory
   - Scan parent directories from cwd
3. Read `repo_local_path` from `instance-config.json`
4. **If not found:** Ask the user for the repo path — do NOT assume a location

## Workflow 1: Check for Updates

**Triggers:** "Check for updates", "Are there new capabilities?", "What's changed in the repo?"

**Steps:**
1. `cd` to the repo and run `git fetch origin` to get latest
2. Compare the current branch against `origin/main` for new commits
3. Run `scripts/compare.py` to diff local `~/.copilot/` against the repo content
4. Present results in categories:

```
📊 Config Sync — Check for Updates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆕 New in repo (not in local):
   • skills/config-sync/SKILL.md
   • personas/new-persona/AGENTS.md

⚠️  Updated in repo (differs from local):
   • personas/productivity/AGENTS.md
   • skills/humanizer/SKILL.md

📁 Local-only (not in repo):
   • skills/my-custom-skill/SKILL.md

✅ Identical: 42 items
```

5. Run `scripts/compare.py` with `--categories templates` to check for template drift
6. If any templates show as `modified`, present them:

```
📄 Templates needing re-render:
   ⚠️  base-instructions — template updated since last render
   ⚠️  instance-rules — template updated since last render
```

   For each modified template:
   - Show the diff: `compare.py <repo> --diff templates <name>` (e.g., `--diff templates base-instructions`)
   - Ask: `[1] Re-render  [2] Skip  [3] Show Diff`
   - If "Re-render": `compare.py <repo> --apply-template <name>` (e.g., `--apply-template base-instructions`)
   - If user has a session reload needed (base instructions changed), remind them: "Base instructions updated — restart your Copilot CLI session to pick up changes."

7. Present the user with structured options (do NOT ask freeform — use numbered choices):

```
What would you like to do?
  [1] Incorporate All — apply all new and updated items to local
  [2] Skip All — keep local as-is, record skips
  [3] Review Each — step through items one at a time (Incorporate / Skip / Show Diff)
```

8. If "Review Each": for each non-identical item, show the item name and status, then ask:
```
  [1] Incorporate  [2] Skip  [3] Show Diff
```
   If "Show Diff": use `compare.py --diff <category> <item_name>` to show the actual differences, then re-prompt with Incorporate/Skip.

9. Update `sync-state.json` with decisions (record skips with reason)

## Workflow 2: Share My Setup

**Triggers:** "Share my setup", "Push my changes", "Sync my local changes to the repo"

**Steps:**
1. Run `scripts/compare.py` to find local changes not in the repo
2. Flag items that contain instance-specific content (paths, account names) — warn before pushing
3. Present changes by category:

```
📤 Config Sync — Share Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Changes to push to 'work' branch:

📝 Modified:
   • personas/architect-marketer/AGENTS.md
   • skills/humanizer/references/voice-profile.md

🆕 New (local-only):
   • skills/my-new-skill/SKILL.md

⚠️  Instance-specific content detected:
   • skills/my-new-skill/SKILL.md contains 'OneDrive - Microsoft'
```

4. Jim approves per-file or per-category
5. Commit and push to the instance branch (work/personal)
6. Update `sync-state.json`

## Workflow 3: Promote to Universal

**Triggers:** "Make this available on both machines", "Promote to main", "Share across instances"

**Steps:**
1. Compare the current instance branch against `main`
2. Show changes that exist on the instance branch but not on main
3. Jim selects which changes to promote
4. Create a commit on `main` (or a PR if preferred)
5. Push to `origin/main`

## Workflow 4: Sync Status

**Triggers:** "What's my sync status?", "Sync dashboard", "Am I up to date?"

**Steps:**
1. Read `sync-state.json` for timestamps and tracked files
2. Check git status for uncommitted local repo changes
3. Check for unpushed commits on the current branch
4. Check for new commits on `origin/main` not yet pulled
5. **Check the active gh CLI account** using `gh api user --jq '.login'` — display it in the dashboard and warn if it doesn't match the expected account from `instance-config.json`
6. Present a dashboard:

```
📊 Config Sync Status
━━━━━━━━━━━━━━━━━━━━

Instance:     work
Branch:       work
GitHub acct:  jimbanach ✅
Last pull:    2026-03-01 12:30 UTC
Last push:    2026-03-01 10:15 UTC

📡 Remote status:
   • 2 new commits on origin/main (not yet pulled)
   • 0 unpushed local commits

📁 Local vs repo:
   • 3 files modified locally
   • 1 new local file
   • 0 repo updates not incorporated

⏭️  Skipped items: 1
   • skills/kql-queries/SKILL.md (reason: "Prefer my local version")
```

## Workflow 5: Publish Template

**Triggers:** "Publish template for peers", "Update the starter repo", "Share with peers"

**Steps:**
1. Run `scripts/sanitize.py` against the `main` branch content
2. Show what will be published with a diff preview vs current template repo
3. Jim reviews and approves
4. Commit and push to `copilot-cli-starter` repo
5. Update CHANGELOG.md in both repos

## Sync State File

Location: `~/.copilot/.copilot-sync/sync-state.json` (gitignored, never shared)

```json
{
  "instance": "work",
  "repo_path": "C:\\Users\\jimbanach\\copilot-cli-config",
  "last_pull": "2026-03-01T12:30:00Z",
  "last_push": "2026-03-01T10:15:00Z",
  "skipped_items": [
    {
      "path": "skills/kql-queries/SKILL.md",
      "repo_sha": "abc123",
      "reason": "Prefer my local version",
      "skipped_at": "2026-03-01T10:00:00Z"
    }
  ],
  "tracked_files": {}
}
```

## Scripts

All scripts are located in **this skill's directory**: `~/.copilot/skills/config-sync/scripts/` (locally) or `skills/config-sync/scripts/` (in the repo). Always run them from the skill's scripts directory, NOT from the repo root.

### `scripts/compare.py`
Computes diffs between local `~/.copilot/` and the repo. Returns JSON with categorized results (new, modified, identical, local-only). Uses line-by-line comparison to ignore CRLF/LF differences. Also compares rendered templates against live deployed files.

Usage:
```bash
python ~/.copilot/skills/config-sync/scripts/compare.py <repo_path> [--copilot-dir <path>] [--json]
python ~/.copilot/skills/config-sync/scripts/compare.py <repo_path> --categories templates  # check templates only
python ~/.copilot/skills/config-sync/scripts/compare.py <repo_path> --diff templates base-instructions  # show template diff
python ~/.copilot/skills/config-sync/scripts/compare.py <repo_path> --apply-template base-instructions  # re-render and deploy
```

### `scripts/sync_state.py`
Tracks pull/push history, skipped items, and sync timestamps.

Usage:
```bash
python ~/.copilot/skills/config-sync/scripts/sync_state.py --state-file <path> <command>
```

### `scripts/sanitize.py`
Sanitizes repo content for the peer template. Replaces user-specific names and paths with `{{variables}}`, blanks the humanizer voice profile, scans for potentially confidential content.

Usage:
```bash
python ~/.copilot/skills/config-sync/scripts/sanitize.py <source_dir> <output_dir> [--user-name "Name"] [--dry-run]
```

## Important Notes

- This skill works **conversationally** — Copilot reads these instructions and uses the tools (terminal, file system) to execute the workflows. The Python scripts handle the heavy computation.
- The skill never force-pushes or auto-merges. Every change requires user approval.
- CHANGELOG.md is updated with every push or publish action.
- The `sync-state.json` is local-only and never committed to the repo.

# Migration Notes — Persona Rename (Issue #72)

> **Delete this file** after completing the migration on all machines.

## What Changed

Persona files renamed from `AGENTS.md` → `persona.instructions.md` with `applyTo: "**"` frontmatter.
This eliminates a naming collision with the industry-standard `AGENTS.md` convention (60k+ repos).

## Work Machine Steps

When you next open the config repo on your **work machine**, run these steps:

### 1. Pull the latest changes
```powershell
cd ~/copilot-cli-config
git checkout work
git pull origin main
# Resolve any merge conflicts if the work branch has diverged
```

### 2. Redeploy with migration
```powershell
pwsh -File init.ps1 -Force
```
The script will:
- Detect legacy `AGENTS.md` files in `~/.copilot/personas/`
- Prompt to migrate them to `persona.instructions.md` with frontmatter
- Deploy the updated persona to `~/.copilot/personas/active/.github/instructions/`
- Clean up old `AGENTS.md` from the active persona directory

### 3. Verify
```powershell
# Check persona loads correctly
pwsh -File ~/.copilot/Switch-CopilotPersona.ps1 -List

# Start a new Copilot CLI session and verify persona content appears
```

### 4. Push starter repo to EMU
```powershell
cd ~/copilot-cli-starter
git pull origin main   # Should already be current
git push emu main      # EMU remote only works from work machine
```

### 5. Clean up
After verifying everything works on the work machine:
```powershell
# Delete this file from the repo
cd ~/copilot-cli-config
git rm MIGRATION-NOTES.md
git commit -m "chore: remove migration notes after successful work machine migration (#72)"
git push origin work
```

## Rollback (if needed)

If anything goes wrong on the work machine:
```powershell
# Restore from backup (if one exists)
Remove-Item ~/.copilot -Recurse -Force
Copy-Item ~/.copilot-backups/<latest-backup> ~/.copilot -Recurse

# Or reset to pre-migration state
git checkout work -- personas/
pwsh -File init.ps1 -Force
```

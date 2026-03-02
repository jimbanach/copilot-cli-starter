## Change Description
<!-- What did you change and why? -->

## Checklist

### Before Merging
- [ ] Change tested locally (Copilot CLI loads correctly, persona switching works)
- [ ] If new skill/agent/persona: verified it triggers correctly
- [ ] If script change: ran with `-DryRun` first
- [ ] No confidential/personal content (names, paths, customer data)

### Documentation
- [ ] CHANGELOG.md updated
- [ ] README.md updated (if the change affects a documented section)
- [ ] PLAN.md updated (if the change affects architecture or process)

### Cross-Repo Sync
- [ ] If change applies to both repos: updated in **copilot-cli-config** AND **copilot-cli-starter**
- [ ] If starter-only: ran `sanitize.py` to verify no personal content leaks
- [ ] If config-only: no action needed for starter

### Testing
- [ ] Automated tests pass (compare.py, sync_state.py — if applicable)
- [ ] UAT completed (describe what you tested below)

### UAT Notes
<!-- What did you test manually? -->

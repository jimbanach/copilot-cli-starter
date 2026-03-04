# Changelog

All notable changes to this configuration are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [2026-03-04] - Upstream sync: OneDrive Known Folder Move support
### Fixed
- `init.ps1`: Auto-detects OneDrive Known Folder Move paths for Desktop and Documents, stores in `instance-config.json`
- Layer 2 instance instructions: Added "Known Folder Paths" section so Copilot saves files to correct redirected locations
- `instance-config.template.json`: Added `known_folders` field

## [2026-03-02b] - Upstream sync: meeting agent cleanup
### Changed
- `meeting-transcript-processor.agent.md`: Now a standalone interactive agent (no longer requires orchestrator)
### Removed
- `meeting-notes-summarizer.agent.md`: Removed (unstable, under rework upstream)
- `meeting-video-analyzer.agent.md`: Removed (unstable, under rework upstream)
### Added
- `.gitignore`: `_disabled/` pattern — agents placed in this local folder are excluded from sync

## [2026-03-02] - Upstream sync: project storage + backlog fixes
### Added
- `New-CopilotProject.ps1`: `-GitHub` flag, cloud-sync detection, forwarding folder pattern
- Base instructions template: "Project Storage Rules" section with `{{GITHUB_PROJECTS_PATH}}`
- `init.ps1`: prerequisites check, account verification, backup retention, github_projects_path prompt
- `.github/pull_request_template.md`: checklist for contributions
### Changed
- `Switch-CopilotPersona.ps1`: detects unsaved edits before switching, CRLF-tolerant comparison
- Config-sync SKILL.md: expanded repo discovery, account display in sync-status
- Template-update SKILL.md: expanded repo discovery paths
- Sync repo: Starter prompts for restore and sync check
- Starter repo: Starter prompts for first-time setup (CLI + VS Code), updates, persona switching

## [2026-03-01] - Phase 4: Config-sync skill
### Added
- `skills/config-sync/SKILL.md` — 5 workflows: check-for-updates, share-setup, promote-to-universal, sync-status, publish-template
- `scripts/compare.py` — line-ending tolerant comparison of local vs repo across personas, skills, agents, scripts
- `scripts/sync_state.py` — tracks pull/push history, skipped items, with CLI interface
- `scripts/sanitize.py` — replaces user names/paths with {{variables}}, blanks voice profile, scans for confidential patterns
- README: config-sync workflows section with mermaid diagram, scripts table, known limitations

## [2026-03-01] - Phase 3: Init script & VS Code support
### Added
- `init.ps1` — interactive initialization script with seed/consume modes and dry-run
- Auto-detects CLI, VS Code, and VS Code Insiders
- Interactive per-category import with Import All / Skip All / Review Each
- Per-item options: Import / Skip / Compare
- Automatic backup before deployment
- VS Code deployment: MCP config, `chat.agentSkillsLocations` for skills discovery
- Template variable resolution for Layer 1 base instructions
- README: init script usage, workflow diagram (mermaid), CLI vs VS Code deployment table

## [2026-03-01] - Phase 2: Content export to repo
### Added
- Exported all 7 personas as lean AGENTS.md files
- Exported 16 skills with scripts and references
- Exported 4 custom agents + scripts
- Exported utility scripts (New-CopilotProject, Switch-CopilotPersona)
- Created `base/copilot-instructions.md.template` with {{variables}}
- Created instance rules: `work.instructions.md` and `personal.instructions.md`
- Created `instance-config.template.json` schema
- Split MCP configs: CLI universal, CLI work, VS Code universal
- README: repo structure tree, branch strategy, exclusions table

## [2026-03-01] - Phase 1: 3-Layer instruction model
### Added
- Layer 1: Base `copilot-instructions.md` with workspace, skills catalog, persona list
- Layer 2: Instance rules (`instance.instructions.md`) with work machine confidentiality guardrails
- Layer 3: Persona AGENTS.md files — lean, role-specific content only
- `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var pointing to `personas/active/`
- Updated `Switch-CopilotPersona.ps1` with `-Target` parameter and new persona auto-detection
- README: 3-layer architecture section with file path reference table and editing guide
- PLAN.md: Full implementation plan
### Changed
- Stripped "Workspace & Tools Awareness" footer from all 7 persona files
- Renamed persona files from `copilot-instructions.md` to `AGENTS.md`
- Switch script now copies to `personas/active/AGENTS.md` instead of overwriting `copilot-instructions.md`
### Removed
- Removed redundant `copilot-instructions.md` files from persona directories (replaced by AGENTS.md)

## [2026-03-01] - Phase 0: Initial repo creation
### Added
- Created repository structure: base/, personas/, skills/, agents/, scripts/, mcp/
- Added CHANGELOG.md, .gitignore, README scaffold
- Added GitHub issue templates (Bug Report, Feature Request, UAT Feedback)

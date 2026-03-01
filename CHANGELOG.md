# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [2026-03-01] - Phase 5b: Upstream update support
### Added
- `skills/template-update/SKILL.md` — skill for checking and pulling upstream template updates
- README: "Pulling Updates" section with upstream remote setup and manual/conversational workflows

## [2026-03-01] - Phase 5a: Initial template population
### Added
- All 7 personas as AGENTS.md files (sanitized — `{{YOUR_NAME}}` and `{{WORKSPACE_PATH}}` variables)
- 16+ skills with scripts and references (portable to CLI and VS Code)
- 4 custom agents + scripts
- Utility scripts (New-CopilotProject.ps1, Switch-CopilotPersona.ps1)
- Interactive init.ps1 setup wizard (auto-detects CLI/VS Code)
- Base instructions template with {{variables}}
- Instance rules for work and personal machines
- MCP configs (CLI universal, CLI work, VS Code universal)
- Blank humanizer voice profile template with build-your-own instructions
- README with quick start, persona table, customization guide, 3-layer architecture diagram

## [2026-03-01] - Phase 0: Initial repo creation
### Added
- Created repository with README scaffold, CHANGELOG.md, .gitignore
- Added GitHub issue templates (Bug Report, Feature Request, UAT Feedback)

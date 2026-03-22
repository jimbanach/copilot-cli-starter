# Changelog

All notable changes to this configuration are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] - v2.0

*Major upgrade in progress — see upstream [copilot-cli-config](https://github.com/jimbanach/copilot-cli-config) for the full plan.*

## [v1.5.1] - 2026-03-22

### Added
- `financial-analyst` persona — fiduciary-minded financial analyst and tax strategist (templated with {{variables}} for privacy)
- `tax-accountant` persona — tax accountant with federal and state tax law expertise (templated with {{variables}} for privacy)
- `code-coach` persona — coding coach for learning and mentoring

### Changed
- `image-generation` SKILL.md: GPT-Image-1.5 as default edit model, medium quality default with cost guidance

## [v1.5] - 2026-03-21

### Changed
- Renamed persona files from `AGENTS.md` to `persona.instructions.md` with `applyTo: "**"` frontmatter (#72)
- Persona deployment path changed to `~/.copilot/personas/active/.github/instructions/persona.instructions.md`
- Updated init.ps1, Switch-CopilotPersona.ps1, compare.py for new persona file format
- Updated switch-persona, config-sync, and agent-builder skills

### Added
- New `persona-creator` skill for guided persona creation and evaluation
- Backward-compatible fallback chain: persona.instructions.md → AGENTS.md → copilot-instructions.md
- Legacy AGENTS.md cleanup during deployment

## [2026-03-18] - WorkIQ proactive usage in Layer 2 work instructions
### Added
- Layer 2 (work): WorkIQ proactive usage guidance — agent now uses `ask_work_iq` for context enrichment, information gap filling, and people context without waiting for explicit requests
- Layer 2 (work): Transparency rule — outputs sourced from WorkIQ marked with 📧
- Layer 2 (work): Per-project opt-out via `workiq_enabled: false` in `project.json`
- Layer 2 (work): Reference to `workiq-productivity` plugin capabilities (email triage, meeting costs, org charts, channel audits)

## [2026-03-18] - Auto-detect environments + code-coach persona (from personal machine)
### Added
- `init.ps1`: Auto-detect available environments — native, WSL, Docker (fixes #18)
- New `code-coach` persona for Minecraft Mod Academy

## [2026-03-17] - Session resume auto-restores project context (fixes #63)
### Added
- Base instructions: On resume, agent now prompts `/cwd` if working directory changed, reads `.github/copilot-instructions.md` into context, and loads the correct persona from `project.json`

## [2026-03-17] - Skill discovery when list is truncated (fixes #69)
### Added
- Base instructions: Skill discovery guidance — when the visible skill list doesn't match a user's request, use `tool_search_tool_regex` to search for hidden skills before giving up

## [2026-03-17] - MCP config merge instead of overwrite (fixes #68)
### Fixed
- `init.ps1` Step 9 now uses JSON-aware merge instead of destructive `Copy-Item -Force` for MCP configs
- Locally-added MCP servers (e.g., azuredevops, image-gen) are preserved across `init.ps1` runs
- Repo-defined servers are updated to latest; servers removed from repo are cleaned up
- Sidecar file (`~/.copilot/mcp-repo-servers.json`) tracks repo-origin servers for removal detection
- DryRun mode shows detailed merge plan (added/updated/preserved/removed)
- Same merge logic applies to both CLI (`mcpServers`) and VS Code (`servers`) configs
### Changed
- `docs/init-script-details.md` updated to reflect actual merge behavior

## [2026-03-14] - Auto-detect available environments in init.ps1 (fixes #18)
### Added
- `init.ps1`: New `Detect-Environments` function that probes for WSL (via `wsl -l -q`) and Docker (via `docker --version`)
- Environment detection runs during init setup and displays results with ✓/✗ indicators and details (distro name, Docker version)
- Auto-detected environments are used as the default instead of hardcoded "native"
- Existing config values still take precedence as defaults when reconfiguring

## [2026-03-14] - Repo transfer from {{YOUR_NAME}}-s-Project-Org to {{YOUR_NAME}}banach
### Changed
- Transferred `copilot-cli-config` and `copilot-cli-starter` from `{{YOUR_NAME}}-s-Project-Org` org to `{{YOUR_NAME}}banach` personal account
- Updated git remote URL to `https://github.com/{{YOUR_NAME}}banach/copilot-cli-config.git`
- Updated starter repo remote reference in `.github/copilot-instructions.md` from `{{YOUR_NAME}}-s-Project-Org` to `{{YOUR_NAME}}banach`
### Fixed
- Built-in GitHub MCP server now has access to the repo (resolves #67) — the MCP token couldn't access private org repos

## [2026-03-14] - Config sync re-renders templates (fixes #66)
### Added
- `compare.py`: New `templates` category that renders `.template` files using `instance-config.json` and compares against live deployed files
- `compare.py`: `--apply-template <name>` flag to re-render and deploy a specific template
- `compare.py`: `--diff templates <name>` shows what changed between rendered template and live file
- Config-sync SKILL.md: Workflow 1 (Check for Updates) now includes template drift detection and re-rendering steps
### Fixed
- Template updates (e.g., new base instructions) are no longer silently missing after sync — compare.py detects drift and prompts for re-rendering

## [2026-03-13] - Save state session naming
### Added
- Base instructions: Save/restore flows now derive a session title from the project folder plus the current date in `MM-DD-YY` format, record it in `.copilot/session-state.md`, and surface the exact `/rename` command for the user
- README: Save State Protocol now documents the session naming convention and `/rename` guidance

## [2026-03-11] - Workstream tagging + cross-repo sync alignment
### Added
- `New-CopilotProject.ps1`: Projects now include a Tracked Workstreams section with tagging table and rules
- Base instructions: Workstream tagging rule — populate workstream table on project setup, tag artifacts with `Workstreams:` metadata
- Project instructions: Dual-push sync rules for starter repo (always push to both origin and emu remotes)
- Starter repo: `playwright-lock.ps1` added, architect-marketer description updated
### Fixed
- Starter README: 11 content drift fixes (mermaid diagram, repo structure, account setup, branch strategy, etc.)
- `productivity/AGENTS.md`: Removed leftover UAT test debris
- Synced voice profile to repo

## [2026-03-10] - Agent sync + Save State Protocol
### Added
- `quiz-content-generator.agent.md`: New agent for generating quiz content
- Base instructions: Save State Protocol — structured `.copilot/session-state.md` file in project folders with session IDs, machine context, status, and resume instructions. Auto-saves at checkpoints, manual trigger with "save my state"
### Changed
- `meeting-transcript-processor.agent.md`: Updated with local improvements

## [2026-03-05] - Bug fixes, persona enforcement, README restructuring, prompt guidance

### Enhanced
- Base instructions: Agent now prompts user to run `/cwd <project-path>` when switching projects or following forwarding-folder redirects, so the CLI status bar shows the correct repo/branch
- Fix #50: Per-project persona enforcement — agent checks `project.json` persona field when opening a project and loads the correct persona if it differs from the active one. Mid-session switches are temporary.
- Fix #61: README restructured with table of contents and anchor links to all sections
- Fix #62: New doc `docs/effective-project-prompts.md` — Full Context Handoff pattern with 6 core elements, 4 recommended additions, annotated real-world example, and copy-paste template
- README: Added Quick Links entry and Prompt Guidance section linking to the new doc

### Fixed
- Fix #60: `init.ps1` now auto-detects OneDrive Known Folder Move paths for Desktop and Documents using `[Environment]::GetFolderPath()` and stores them in `instance-config.json` under `known_folders`
- Layer 2 instance instructions now include a "Known Folder Paths" section so Copilot saves files to the correct redirected locations
- `instance-config.template.json` updated with `known_folders` field
- Fix #55: `compare.py` now respects `_disabled/` folder — agents in local `_disabled/` are excluded from `local_only` results, preventing incorrect re-sync
- Fix #40: `init.ps1` now detects local-only items (removed from repo) during consume and offers Delete All / Skip All / Review Each options
- Fix #48: `New-CopilotProject.ps1` now handles `-GitHub -Environment wsl` correctly — creates project in GitHubProjects with forwarding folder instead of delegating to WSL script
- README: Documented `_disabled/` convention and `instance-config.json` in "What's NOT in the Repo" table
- `init.ps1`: Added UTF-8 BOM so PowerShell 5.1 correctly parses Unicode characters (fixes #59)

### Changed
- README: Streamlined init script "What It Does" section — replaced full mermaid diagram with concise numbered steps
- Moved detailed init workflow diagram and step-by-step breakdown to `docs/init-script-details.md`
- README: Added "Init Script Details" to Quick Links section

## [2026-03-02b] - Meeting agent cleanup
### Changed
- `meeting-transcript-processor.agent.md`: Now a standalone interactive agent (no longer requires orchestrator)
### Removed
- `meeting-notes-summarizer.agent.md`: Disabled (moved to local `_disabled/`)
- `meeting-video-analyzer.agent.md`: Disabled (moved to local `_disabled/`)
### Added
- `.gitignore`: `_disabled/` pattern — agents placed in this local folder are excluded from sync

## [v1.0] - 2026-03-02 — Initial Platform Release

## [2026-03-02] - Backlog fixes + Project storage (#47)
### Added
- `New-CopilotProject.ps1`: `-GitHub` flag for GitHub-backed projects, cloud-sync detection, forwarding folder pattern (project.json + MOVED-TO-GITHUB.md + .lnk + copilot-instructions.md redirect)
- Layer 1 base: "Project Storage Rules" section with forwarding folder guidance
- `init.ps1`: prerequisites check (git, gh, python required; PowerShell 6+, Node.js optional)
- `init.ps1`: GitHub account verification before proceeding
- `init.ps1`: `github_projects_path` prompt and instance-config field
- `init.ps1`: backup retention policy (subfolder `~/.copilot-backups/`, keep last 3)
- README: "Account Setup" section with account table and switching instructions
- README: "How To" quick reference table
- README: "Starter Prompts" section
- README: "Reviewing Peer PRs" section
- `.github/copilot-instructions.md`: project-level instructions for consistent process
- `.github/pull_request_template.md`: checklist for testing, docs, cross-repo sync
### Changed
- `Switch-CopilotPersona.ps1`: detects unsaved active persona edits before switching (closest-match detection for edited personas)
- `Switch-CopilotPersona.ps1`: line-by-line comparison for CRLF tolerance
- Config-sync SKILL.md: sync-status shows active GitHub account, expanded repo discovery paths
- Base template: added `{{GITHUB_PROJECTS_PATH}}` variable
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

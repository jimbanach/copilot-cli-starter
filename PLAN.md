# Plan: Portable Copilot CLI Configuration with Smart Sync

## Problem Statement

{{YOUR_NAME}} has built a mature Copilot CLI environment (7 personas, 16 skills, 4 agents, utility scripts, MCP configs) on his work machine. He needs to:

1. **Sync between his own machines** — bidirectional, selective sync between work and personal laptops, keeping company-confidential projects isolated
2. **Share as a template for peers** — a sanitized, getting-started version that others can use to bootstrap their own Copilot CLI workspace
3. **Restore easily** — if he sets up a new machine, he should be able to run a single prompt that rebuilds the full environment

This is NOT a one-time export. It's an ongoing system with three tiers: private sync, public template, and guided onboarding.

## Proposed Approach

### Architecture: Two Repos + Sync Skill

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                      PRIVATE REPO                               │
  │                  copilot-cli-config                             │
  │                                                                 │
  │   main ← universal baseline (both machines share)               │
  │   work ← work-specific overrides                                │
  │   personal ← personal-specific overrides                        │
  │                                                                 │
  └──────┬───────┬─────────────────────┬────────────────────────────┘
         │       │                     │
  push/pull   push/pull          sanitize & publish
         │       │                     │
    ┌────┘       └────┐                ▼
    ▼                  ▼          ┌──────────────────────────┐
  ┌────────────┐  ┌────────────┐  │  PRIVATE TEMPLATE REPO   │
  │ Work       │  │ Personal   │  │  copilot-cli-starter     │
  │ Machine    │  │ Laptop     │  │                          │
  │ ~/.copilot │  │ ~/.copilot │  │  Lightly sanitized       │
  │            │  │            │  │  Shared via collaborator │
  │ instance-  │  │ instance-  │  │  access to MS peers      │
  │ config.json│  │ config.json│  └──────────────────────────┘
  └────────────┘  └────────────┘           │
                                    fork / clone
                                           │
                                    ┌──────┴──────┐
                                    │  Peer's Copy│
                                    │  Their own  │
                                    │  workspace  │
                                    └─────────────┘
```

### Two-Repo Strategy (Both Private)

| Repo | Visibility | Purpose |
|------|-----------|---------|
| `copilot-cli-config` | **Private** | {{YOUR_NAME}}'s bidirectional sync between work & personal machines |
| `copilot-cli-starter` | **Private** | Sanitized template for Microsoft peers (shared via collaborator access) |

Both repos are private. {{YOUR_NAME}} shares `copilot-cli-starter` by adding specific Microsoft peers as collaborators. Since all recipients are internal to Microsoft, the sanitization bar is lower — publicly documented product names, role descriptions, and Microsoft tooling references are fine. Only truly confidential content (customer data, NDA materials, project-specific strategies) needs scrubbing.

The starter repo is a **one-way downstream**: {{YOUR_NAME}} periodically publishes sanitized snapshots from his private `main` branch. Peers never push back to it — they fork and own their own setup.

### Branch Strategy (Private Repo)

| Branch | Purpose | Who pushes |
|--------|---------|------------|
| `main` | Universal config — shared across all instances | Either machine, after review |
| `work` | Work-specific additions/overrides (e.g., WorkIQ MCP, OneDrive paths) | Work machine only |
| `personal` | Personal-specific additions/overrides | Personal laptop only |

**Workflow:** Make changes locally → sync skill compares local vs repo → selectively push to instance branch → when something is universal, PR/merge to `main` → when ready to share with peers, run "publish template" workflow.

### Repo Structure

```
copilot-cli-config/
├── README.md                          # Setup guide & architecture docs
├── init.ps1                           # First-time initialization script
├── instance-config.template.json      # Template for per-instance settings
├── .gitignore                         # Excludes instance-config.json, sync-state
│
├── base/
│   ├── copilot-instructions.md.template  # Layer 1: Universal base with {{variables}}
│   └── instance-rules/
│       ├── work.instructions.md          # Layer 2: Work machine rules (confidentiality, paths)
│       └── personal.instructions.md      # Layer 2: Personal machine rules
│
├── personas/
│   ├── productivity/
│   │   └── persona.instructions.md                 # Layer 3: Role-specific content only
│   ├── deep-technical/
│   │   └── persona.instructions.md
│   ├── security-architect/
│   │   └── persona.instructions.md
│   ├── marketing/
│   │   └── persona.instructions.md
│   ├── program-manager/
│   │   └── persona.instructions.md
│   ├── architect-marketer/
│   │   └── persona.instructions.md
│   └── hypervelocity-engineer/
│       └── persona.instructions.md
│
├── skills/
│   ├── agent-builder/          (SKILL.md + references/ + scripts/)
│   ├── content-drafting/       (SKILL.md)
│   ├── docx/                   (SKILL.md + scripts/ + LICENSE)
│   ├── email-triage/           (SKILL.md)
│   ├── environment-advisor/    (SKILL.md + setup-wsl-project.ps1)
│   ├── humanizer/              (SKILL.md + scripts/ + references/voice-profile.md)
│   ├── kql-queries/            (SKILL.md)
│   ├── meeting-prep/           (SKILL.md)
│   ├── pdf/                    (SKILL.md + scripts/ + reference docs)
│   ├── pptx/                   (SKILL.md + scripts/ + reference docs)
│   ├── project-status/         (SKILL.md)
│   ├── remote-github-repo/     (SKILL.md + references/)
│   ├── research/               (SKILL.md)
│   ├── skill-creator/          (SKILL.md + scripts/ + references/)
│   ├── switch-persona/         (SKILL.md)
│   ├── xlsx/                   (SKILL.md + scripts/)
│   └── config-sync/            (NEW — the sync skill itself)
│       ├── SKILL.md
│       └── scripts/
│           └── compare.py
│
├── agents/
│   ├── meeting-notes-summarizer.agent.md
│   ├── meeting-transcript-processor.agent.md
│   ├── meeting-video-analyzer.agent.md
│   ├── slide-architect.agent.md
│   └── scripts/
│       └── extract_video_frames.py
│
├── scripts/
│   ├── New-CopilotProject.ps1
│   └── Switch-CopilotPersona.ps1
│
└── mcp/
    ├── mcp-config.universal.json      # MCPs that work everywhere (Playwright, MS Docs)
    └── mcp-config.work.json           # Work-only MCPs (WorkIQ) — only on work branch
```

### What's Excluded (NEVER in the repo)

| Item | Reason |
|------|--------|
| `config.json` | Contains GitHub login, model preferences — instance-specific |
| `permissions-config.json` | Contains local filesystem paths |
| `session-state/` | Active session data |
| `session-store.db*` | Chat history — private per machine |
| `logs/` | Runtime logs |
| `command-history-state.json` | Command history |
| `CopilotWorkspace/` projects | Company-confidential project data |
| `GitHubProjects/` projects | Company-confidential project data |
| `_shared-resources/` | Work-internal shared materials |
| `__pycache__/`, `*.pyc` | Python bytecode |

### Instance Configuration

Each machine gets a local `instance-config.json` (gitignored) created during init:

```json
{
  "instance_name": "work",
  "user_display_name": "{{YOUR_NAME}}",
  "workspace_path": "{{WORKSPACE_PATH}}",
  "project_script_path": "~/.copilot/New-CopilotProject.ps1",
  "github_account": "{{YOUR_NAME}}banach_microsoft",
  "available_environments": ["native", "wsl", "docker"],
  "docker_version": "29.2.0",
  "mcp_profile": "work",
  "repo_remote": "git@github.com:{{YOUR_NAME}}banach_microsoft/copilot-cli-config.git",
  "repo_local_path": "~/copilot-cli-config",
  "branch": "work"
}
```

Personal instance would have:
```json
{
  "instance_name": "personal",
  "user_display_name": "{{YOUR_NAME}}",
  "workspace_path": "~/OneDrive/CopilotWorkspace",
  "github_account": "{{YOUR_NAME}}banach",
  "available_environments": ["native", "wsl", "docker"],
  "mcp_profile": "universal",
  "branch": "personal"
}
```

### Persona Architecture: Native 3-Layer Model (Verified ✅)

Copilot CLI natively loads instructions from multiple locations simultaneously. We leverage this with a **three-layer architecture**, verified by testing that all three layers load and respond to layer-specific queries independently.

**Environment setup (one-time, per machine):**
```
COPILOT_CUSTOM_INSTRUCTIONS_DIRS = ~/.copilot/personas/active
```

Copilot CLI then loads from this directory: `.github/instructions/persona.instructions.md` (persona) + `.github/instructions/*.instructions.md` (instance rules). Combined with the always-loaded `copilot-instructions.md`, this gives us three layers:

| Layer | File | Content | When it changes |
|-------|------|---------|-----------------|
| **1. Universal Base** | `~/.copilot/copilot-instructions.md` | Workspace structure, skills catalog, general behaviors, tool usage, persona list | Rarely — only when adding skills, changing workspace structure, or updating universal behaviors |
| **2. Instance Rules** | `~/.copilot/personas/active/.github/instructions/instance.instructions.md` | Machine-specific rules (work: confidentiality, OneDrive paths, WorkIQ; personal: personal-specific preferences) | Once during init; edited manually when instance rules change |
| **3. Active Persona** | `~/.copilot/personas/active/.github/instructions/persona.instructions.md` | Role-specific tone, behaviors, domain focus areas ONLY | Every persona switch (script copies from persona library) |

**How it works:**
- `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var points to `~/.copilot/personas/active/`
- Copilot CLI loads all three files automatically on every session start
- Persona switch script copies the selected persona's `persona.instructions.md` into `active/.github/instructions/` — **Layers 1 and 2 are never touched**
- The `instance.instructions.md` uses `applyTo: "**"` frontmatter to apply to all file contexts

**What each layer owns (clear boundaries):**

Layer 1 — Universal Base:
- CopilotWorkspace structure and project awareness
- Available skills list and descriptions
- Available personas list
- Environment capabilities (WSL, Docker versions)
- General tool usage patterns
- How to use `New-CopilotProject.ps1` and `Switch-CopilotPersona.ps1`

Layer 2 — Instance Rules:
- **Work machine:** confidentiality guardrail, OneDrive paths, WorkIQ MCP guidance, work GitHub account context
- **Personal machine:** personal workspace paths, personal preferences, personal GitHub account context
- Any rules that should apply to ALL personas but only on THIS machine

Layer 3 — Active Persona:
- Tone & style
- Core focus areas and domain expertise
- Behavioral rules specific to the role
- Custom tools/agents/skills that are ONLY availble to this role (should be rare)
- NO workspace/tools/environment info (that's Layer 1)
- NO confidentiality rules (that's Layer 2)

**Benefits:**
- No 7x duplication of workspace awareness or confidentiality rules
- No assembly scripts or templating needed — Copilot CLI handles it natively
- Base instructions and instance rules survive every persona switch
- Adding a new skill or tool = edit Layer 1 once, all personas benefit
- Work-specific rules never leak to personal machine (different Layer 2 content)
- New skills/tools/environment changes propagate instantly to all personas

**Persona library structure in the repo:**
```
personas/
├── productivity/persona.instructions.md        # Role-specific content only (~1-3KB each)
├── deep-technical/persona.instructions.md
├── security-architect/persona.instructions.md
├── marketing/persona.instructions.md
├── program-manager/persona.instructions.md
├── architect-marketer/persona.instructions.md
└── hypervelocity-engineer/persona.instructions.md
```

**Base and instance templates in the repo:**
```
base/
├── copilot-instructions.md.template    # Universal base with {{WORKSPACE_PATH}}, {{USER_NAME}} vars
└── instance-rules/
    ├── work.instructions.md            # Work machine instance rules
    └── personal.instructions.md        # Personal machine instance rules
```

**Local structure after init:**
```
~/.copilot/
├── copilot-instructions.md                              # Layer 1: Universal base (resolved)
├── personas/
│   ├── active/
│   │   ├── .github/
│   │   │   └── instructions/
│   │   │       ├── persona.instructions.md                  # Layer 3: Currently active persona
│   │   │       └── instance.instructions.md             # Layer 2: Instance-specific rules
│   ├── productivity/persona.instructions.md                           # Persona library
│   ├── deep-technical/persona.instructions.md
│   ├── security-architect/persona.instructions.md
│   ├── marketing/persona.instructions.md
│   ├── program-manager/persona.instructions.md
│   ├── architect-marketer/persona.instructions.md
│   └── hypervelocity-engineer/persona.instructions.md
├── skills/...
├── agents/...
└── scripts/...
```

---

## The Config-Sync Skill

### SKILL.md Design

The config-sync skill is the heart of the system. It provides these workflows:

#### 1. "Check for updates" — Pull-side review
```
User: "Check if there are any new capabilities for me to incorporate"
```
- Fetches latest from the repo (main + instance branch)
- Compares repo files against local `~/.copilot/` files
- Shows a categorized diff:
  - **New in repo** — files that exist in repo but not locally
  - **Updated in repo** — files that differ from local versions
  - **Local-only** — files that exist locally but not in repo
  - **Identical** — files that match
- For each difference, shows a preview, explains what is new and asks {{YOUR_NAME}} to: Incorporate / Skip / Review later

#### 2. "Share my setup" — Push-side review
```
User: "Share my most recent setup for personal use"
```
- Scans local `~/.copilot/` against the repo
- Flags items that look instance-specific (paths, account names, MCP configs)
- Shows what would be pushed, what it does, and to which branch
- {{YOUR_NAME}} approves per-file or per-category
- Commits and pushes to the instance branch

#### 3. "Promote to universal" — Cross-instance sharing
```
User: "Make the humanizer improvements available on both machines"
```
- Identifies changes on the current instance branch that aren't on main
- {{YOUR_NAME}} selects which changes to promote
- Creates a commit (or PR) to merge into main

#### 4. "Sync status" — Dashboard
```
User: "What's my sync status?"
```
- Shows last sync timestamp per branch
- Lists pending changes in either direction
- Flags any merge conflicts

### Sync State Tracking

Local `~/.copilot/.copilot-sync/sync-state.json` (gitignored):
```json
{
  "last_pull": "2026-02-28T18:00:00Z",
  "last_push": "2026-02-28T17:30:00Z",
  "skipped_items": [
    {
      "path": "skills/kql-queries/SKILL.md",
      "repo_sha": "abc123",
      "reason": "Prefer my local version",
      "skipped_at": "2026-02-28T17:30:00Z"
    }
  ],
  "tracked_files": {
    "personas/productivity/persona.instructions.md": {
      "local_sha": "def456",
      "repo_sha": "def456",
      "status": "synced"
    }
  }
}
```

---

## Initialization Flow

### First Time (Work Machine — seeding the repo)

1. **Run `init.ps1`** from the repo root (or {{YOUR_NAME}} runs the script we create)
2. Script prompts for instance details (name, paths, environments)
3. Script creates `instance-config.json` locally
4. Script exports current `~/.copilot/` content into the repo structure:
   - Personas (split into core + common footer)
   - Skills (copy SKILL.md + scripts + references, skip __pycache__)
   - Agents (copy .agent.md files + scripts)
   - Scripts (New-CopilotProject.ps1, Switch-CopilotPersona.ps1)
   - MCP configs (split into universal vs work-specific)
5. Script creates the `config-sync` skill in `~/.copilot/skills/config-sync/`
6. Script commits to `work` branch, then creates `main` from it
7. Pushes to GitHub

### First Time (Personal Laptop — consuming the repo)

1. Clone the repo: `git clone git@github.com:{{YOUR_NAME}}banach_microsoft/copilot-cli-config.git`
2. Checkout `personal` branch (created from `main`)
3. Run `init.ps1`
4. Script prompts for instance details
5. Script assembles personas (core + workspace footer with personal paths)
6. Script copies skills, agents, and scripts to `~/.copilot/`
7. Script generates `mcp-config.json` from universal template
8. Script installs the `config-sync` skill
9. Done — Copilot CLI is fully configured

### Ongoing Sync (either machine)

1. "Hey, check for updates" → config-sync skill runs
2. Reviews diffs, presents choices
3. {{YOUR_NAME}} selects what to incorporate
4. Skill updates local files and records decisions in sync-state.json

---

## Confidentiality Safeguards

1. **`.gitignore` is strict** — config.json, permissions, sessions, logs, __pycache__ are all excluded
2. **CopilotWorkspace and GitHubProjects projects are NEVER in the repo** — they stay in OneDrive/local only
3. **MCP configs are split** — WorkIQ stays on the work branch only
4. **Sync skill flags instance-specific content** — if a file contains patterns like `OneDrive - Microsoft`, `{{YOUR_NAME}}banach_microsoft`, or work-specific paths, it warns before pushing to main
5. **Branch isolation** — work branch and personal branch never need to be checked out on the wrong machine
6. **Sync state tracks skips** — if {{YOUR_NAME}} says "don't sync this" for a file, it remembers and won't ask again until the file changes
7. **Template repo is internal-only** — private repo shared via collaborator access; peers are Microsoft employees

---

## Copilot Instructions Update: Confidentiality Guardrails

The confidentiality guardrail lives in **Layer 2 (Instance Rules)**, not the universal base. This means:
- On the **work machine**: `instance.instructions.md` includes the confidentiality rules below
- On the **personal machine**: `instance.instructions.md` can have different rules (e.g., "don't reference work projects")
- The guardrail applies to ALL personas because Layer 2 loads alongside every persona switch

### Work Instance Rules (`base/instance-rules/work.instructions.md`)

```markdown
---
applyTo: "**"
---
# Instance Configuration: Work Machine

## Identity
- This is the **work machine** instance
- Workspace root: {{WORKSPACE_PATH}}
- GitHub account: {{GITHUB_ACCOUNT}}

## Confidentiality Rules
- Before including information that may be confidential or highly confidential in any output that will be stored outside the current project folder (e.g., committed to a repo, shared in a document, exported, or synced), ask for user confirmation first
- Examples of potentially confidential content: customer names, partner-specific strategies, NDA-protected materials, internal org structures, unreleased roadmap details, specific revenue or engagement data
- Content that is NOT confidential: publicly documented Microsoft product names and features, general role descriptions, publicly available frameworks and methodologies, Microsoft Learn content
- When in doubt, flag it and ask: "This may contain confidential information. Should I include it?"
- This does NOT apply to content that stays within the local project folder or session

## Work-Specific Tools
- WorkIQ is available for email and calendar access via the workiq MCP server
- OneDrive - Microsoft is available for file storage and sharing
```

### Personal Instance Rules (`base/instance-rules/personal.instructions.md`)

```markdown
---
applyTo: "**"
---
# Instance Configuration: Personal Machine

## Identity
- This is the **personal machine** instance
- Workspace root: {{WORKSPACE_PATH}}
- GitHub account: {{GITHUB_ACCOUNT}}

## Personal Rules
- Do not reference or attempt to access work projects, work email, or work-specific tools
- This environment is for personal projects, learning, and experimentation
- No company-confidential information should be present on this machine
```

---

## Peer Template Repo: `copilot-cli-starter`

### Purpose

A lightly sanitized version of {{YOUR_NAME}}'s setup, shared as a private repo with specific Microsoft peers via collaborator access. Supports **both Copilot CLI and VS Code** users with dual deployment paths.

It ships with:
- Template personas (all 7 with customization prompts)
- All skills (portable — same format works in both CLI and VS Code)
- Agent definitions (shared format between CLI and VS Code)
- Dual init scripts (auto-detects CLI vs VS Code and deploys accordingly)
- A comprehensive README with copy-paste starter prompts for both clients

### Dual Client Support: CLI vs VS Code

The init script auto-detects which Copilot client(s) the user has by checking for:
- **CLI:** `~/.copilot/config.json` exists
- **VS Code:** `%APPDATA%/Code/User/settings.json` exists
- **VS Code Insiders:** `%APPDATA%/Code - Insiders/User/settings.json` exists

If it can't determine, it asks the user. If both are present, it offers to configure both.

#### Deployment Path Comparison

| Component | CLI Deployment | VS Code Deployment |
|-----------|---------------|-------------------|
| **Layer 1: Base instructions** | `~/.copilot/copilot-instructions.md` | `%APPDATA%/Code/User/instructions/base.instructions.md` (via `chat.instructionsFilesLocations` setting) |
| **Layer 2: Instance rules** | `~/.copilot/personas/active/.github/instructions/instance.instructions.md` (via env var) | `%APPDATA%/Code/User/instructions/instance.instructions.md` |
| **Layer 3: Active persona** | `~/.copilot/personas/active/.github/instructions/persona.instructions.md` (via env var) | `%APPDATA%/Code/User/agents/active-persona.agent.md` (user-profile agent) |
| **Persona library** | `~/.copilot/personas/*/persona.instructions.md` | `%APPDATA%/Code/User/copilot-personas/*/persona.instructions.md` (custom dir) |
| **Persona switching** | `Switch-CopilotPersona.ps1` copies to `active/.github/instructions/persona.instructions.md` | `Switch-CopilotPersona.ps1` copies to VS Code user agents dir |
| **Agents** | `~/.copilot/agents/*.agent.md` | `%APPDATA%/Code/User/agents/*.agent.md` (user profile) |
| **Skills** | `~/.copilot/skills/*/SKILL.md` | `~/.copilot/skills/*/SKILL.md` (same!) + `.github/skills/` + configurable via `chat.agentSkillsLocations` |
| **MCP servers** | `~/.copilot/mcp-config.json` | `%APPDATA%/Code/User/mcp.json` (slightly different schema) |
| **Env var** | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | `chat.instructionsFilesLocations` setting |

**Note on Skills:** Agent Skills is an [open standard](https://agentskills.io) — the same `SKILL.md` format and `~/.copilot/skills/` location works in both CLI and VS Code. VS Code also supports project-level skills in `.github/skills/` and additional locations via the `chat.agentSkillsLocations` setting. Skills created for CLI are **fully portable** to VS Code.

#### What VS Code Users Get vs CLI Users

| Capability | CLI | VS Code | Notes |
|-----------|-----|---------|-------|
| 3-layer instruction model | ✅ Full native support | ✅ Via settings + user profile | Different mechanism, same result |
| Persona switching | ✅ Script + env var | ✅ Script + user agents | Script handles both paths |
| Custom skills | ✅ Full support | ✅ Full support (same SKILL.md, same `~/.copilot/skills/`) | Open standard — fully portable |
| Custom agents | ✅ `~/.copilot/agents/` | ✅ User profile agents | Same .agent.md format |
| MCP servers | ✅ mcp-config.json | ✅ mcp.json | Init generates correct format per client |
| Workspace projects | ✅ CopilotWorkspace | ✅ Standard VS Code workspaces | Different project structure |

#### Init Script Detection Logic

```powershell
# Auto-detection
$hasCLI = Test-Path "$env:USERPROFILE\.copilot\config.json"
$hasVSCode = Test-Path "$env:APPDATA\Code\User\settings.json"
$hasInsiders = Test-Path "$env:APPDATA\Code - Insiders\User\settings.json"

# If both detected, ask which to configure
# If only one detected, confirm and proceed
# If neither detected, ask user which they plan to use
```

#### Switch Script Update

`Switch-CopilotPersona.ps1` gains a `-Target` parameter and **auto-detects new personas**:

```powershell
Switch-CopilotPersona.ps1 -Persona productivity                    # Auto-detects target(s)
Switch-CopilotPersona.ps1 -Persona productivity -Target cli         # CLI only
Switch-CopilotPersona.ps1 -Persona productivity -Target vscode      # VS Code only
Switch-CopilotPersona.ps1 -Persona productivity -Target all         # Both
```

**New persona auto-detection:** On every run, the script scans `~/.copilot/personas/` for subdirectories containing `persona.instructions.md`. If it finds a persona that isn't listed in the Layer 1 base `copilot-instructions.md` (in the "Available Personas" section), it automatically adds it. This means:
- Drop a new persona folder into `~/.copilot/personas/` 
- Next time you switch personas (or run with `-List`), the script adds it to the base instructions
- Copilot immediately knows about the new persona without manual edits to Layer 1

### Sanitization Rules (Lighter Touch — Internal Audience)

Since peers are Microsoft-internal, most content is safe as-is. Sanitization focuses on:

| Content | Treatment |
|---------|-----------|
| User name ("{{YOUR_NAME}}") | Replaced with `{{YOUR_NAME}}` placeholder |
| Workspace paths (OneDrive - Microsoft) | Replaced with `{{WORKSPACE_PATH}}` |
| Humanizer voice profile | Replaced with blank template + instructions to build your own (voice is too personal) |
| Microsoft product references, role titles | **Kept as-is** — peers understand the context |
| Persona domain-specific content | **Kept as-is** — serves as examples of how to build role-specific personas |
| MCP configs | Universal set included; WorkIQ referenced with setup instructions |
| Skills, agents, scripts | **Included as-is** — fully functional tooling |

**What DOES get scrubbed:**
- Any content that references specific confidential projects, customer names, or NDA-protected strategies
- The config-sync skill's "publish template" workflow flags anything that looks potentially confidential or workspace specific for {{YOUR_NAME}} to review before inclusion

### Template Persona Strategy

Since all peers are Microsoft-internal, personas transfer with minimal changes:

**All 7 personas included as-is** (with `{{YOUR_NAME}}` and `{{WORKSPACE_PATH}}` variables in the footer). Peers can:
- Use them directly if the role fits
- Use them as examples to build their own role-specific personas
- Each persona includes a comment at the top: `<!-- This persona can be customized for your specific role. See the Customization Guide in README.md -->`

### Publish Workflow (config-sync skill, workflow #5)

```
User: "Publish a new template snapshot for peers"
```
1. Reads `main` branch content
2. Runs sanitization (name/path replacement, voice profile blanking, Tier 2 persona annotation)
3. Shows {{YOUR_NAME}} what will be published with a diff preview
4. {{YOUR_NAME}} approves
5. Commits to the private `copilot-cli-starter` repo

---

## README Starter Prompts

The README includes copy-paste prompts for three scenarios. These are designed to be pasted directly into Copilot CLI on a fresh machine.

### Prompt 1: "I'm {{YOUR_NAME}} restoring my setup on a new machine"

```markdown
## 🔄 Restore My Copilot CLI Setup

Copy this into Copilot CLI on your new machine:

I need to restore my Copilot CLI environment from my config repo. Here's what to do:

1. Clone my private repo: git clone git@github.com:{{YOUR_NAME}}banach_microsoft/copilot-cli-config.git ~/copilot-cli-config
2. Run the init script: ~/copilot-cli-config/init.ps1
3. When prompted, configure this as my [work/personal] instance
4. After setup, verify by running: Switch-CopilotPersona.ps1 -List

The repo has my personas, skills, agents, and scripts. The init script will:
- Ask which instance this is (work or personal)
- Assemble my personas with the right workspace paths
- Copy all skills and agents to ~/.copilot/
- Generate the right mcp-config.json for this instance
- Install the config-sync skill so I can stay in sync going forward
```

### Prompt 2: "I'm a peer setting up Copilot CLI for the first time"

```markdown
## 🚀 Get Started with Copilot CLI

Copy this into Copilot CLI after installing it:

I want to set up a productive Copilot CLI workspace using the copilot-cli-starter template.
Please help me by:

1. Forking the template repo to my GitHub account (or cloning if I already did)
2. Running the init script which will ask me:
   - My name (for persona personalization)
   - My workspace folder path (where I want projects to live)
   - Which personas I want to activate (show me the options)
   - What development environments I have available (native/WSL/Docker)
   - Which MCP servers I want to enable
3. After setup, give me a quick tour of:
   - How to switch between personas
   - What skills are available and when they auto-trigger
   - How to create a new project
   - How to customize a persona for my specific role

The template includes starter personas, productivity skills, and
project management tools. Walk me through making them my own.
```

### Prompt 2b: "I'm a peer using VS Code (not CLI)"

```markdown
## 🚀 Get Started with Copilot in VS Code

Copy this into Copilot Chat in VS Code:

I want to set up a productive Copilot workspace using the copilot-cli-starter template.
I use VS Code (not the CLI). Please help me by:

1. Cloning the template repo if I haven't already
2. Running the init script which will:
   - Detect that I'm using VS Code
   - Ask my name and workspace path
   - Deploy instructions to my VS Code user profile
   - Deploy skills, agents, and MCP servers for VS Code
   - Install the persona library and switch script
3. After setup, show me:
   - How to switch between personas
   - What skills are available (type /skills in chat)
   - What agents are available
   - What MCP servers are configured
   - How to customize a persona for my specific role

Skills, agents, and personas all work in VS Code using the same
format as the CLI. The init script handles all the deployment.
```

### Prompt 3: "I'm {{YOUR_NAME}} and I want to check what's changed since my last sync"

```markdown
## 🔍 Sync Check

Check my Copilot CLI config sync status. I want to know:
- Are there any new capabilities in the repo I haven't incorporated locally?
- Have I made local changes that haven't been pushed to the repo yet?
- Is my config-sync state healthy?

Run the config-sync skill's "check for updates" workflow.
```

---

## Implementation Approach: Phased Rollout with Gates

Each phase is self-contained — it delivers working value and is tested/confirmed before moving to the next. Each phase has both **automated tests** (scripts that verify expected state) and **UAT steps** (manual verification by {{YOUR_NAME}}). Issues found during UAT are filed as GitHub Issues in the `copilot-cli-config` repo.

### Documentation as We Go

Documentation is NOT deferred to Phase 6. **Every phase updates docs incrementally:**

- **CHANGELOG.md** — updated with every commit, in both repos
- **README.md** — each phase adds/updates sections relevant to what was built. Phase 6 is a final review and polish pass, not a from-scratch write.
- **Inline comments** — scripts and config files are documented as they're created

| Phase | Docs Produced |
|-------|--------------|
| 0 | Initial README scaffolds + CHANGELOG + issue templates |
| 1 | README section: 3-layer architecture, persona switching how-to |
| 2 | README section: repo structure, what's included, branch strategy |
| 3 | README section: init script usage, CLI vs VS Code deployment |
| 4 | README section: config-sync workflows, sync status how-to |
| 5a | Template README: getting started, peer onboarding prompts |
| 5b | Template README: pulling upstream updates |
| 5c | CONTRIBUTING.md, PR review workflow docs |
| 6 | **Final review & polish** — stitch all sections together, verify accuracy, test prompts, ensure no stale references |

### Phase 0: Repo Creation & Issue Tracking (First!)
**Goal:** Create both repos immediately so we have issue tracking, changelogs, and version control from day one. All subsequent work is committed incrementally.

| # | Todo | Description |
|---|------|-------------|
| 1 | **create-sync-repo** | Create private `copilot-cli-config` repo on GitHub with README, CHANGELOG.md, .gitignore, and issue templates/ A copy of this plan should be stored in this repo as well |
| 2 | **create-template-repo** | Create private `copilot-cli-starter` repo on GitHub with README, CHANGELOG.md, .gitignore, and issue templates |
| 3 | **setup-issue-templates** | Create issue templates for both repos: Bug Report, Feature Request, UAT Feedback |
| 4 | **clone-locally** | Clone `copilot-cli-config` to work machine; set up `work` and `main` branches |

**Phase 0 Gate:**
- **Automated:** Script verifies both repos exist, have CHANGELOG.md, .gitignore, issue templates, and initial README scaffolds
- **UAT:** {{YOUR_NAME}} confirms repos are accessible, can create issues, branches are correct, READMEs have placeholder structure

---

### Phase 0.5: Full Local Backup
**Goal:** Take a complete backup of the current working Copilot CLI setup before any changes. Establish a documented restore process so {{YOUR_NAME}} can roll back to the exact current state if anything breaks.

| # | Todo | Description |
|---|------|-------------|
| 5 | **backup-copilot-dir** | Create a full timestamped backup of `~/.copilot/` (personas, skills, agents, scripts, configs, instructions — everything except session-state and logs) |
| 6 | **backup-env-vars** | Capture current relevant environment variables (COPILOT_CUSTOM_INSTRUCTIONS_DIRS if set, any other Copilot-related vars) |
| 7 | **backup-vscode-config** | Backup VS Code Copilot-related config: `%APPDATA%/Code/User/mcp.json`, relevant `settings.json` entries, any user-profile agents |
| 8 | **document-restore-process** | Create a `RESTORE.md` in the backup directory with step-by-step instructions to restore from this backup |

**Backup contents:**
```
~/.copilot-backup-YYYY-MM-DD-HHMMSS/
├── RESTORE.md                    # Step-by-step restore instructions
├── env-snapshot.json             # Environment variable snapshot
├── copilot/                      # Full copy of ~/.copilot/
│   ├── copilot-instructions.md
│   ├── config.json
│   ├── mcp-config.json
│   ├── permissions-config.json
│   ├── New-CopilotProject.ps1
│   ├── Switch-CopilotPersona.ps1
│   ├── personas/                 # All persona dirs with persona.instructions.md (renamed from AGENTS.md, see #72)
│   ├── skills/                   # All skill dirs
│   └── agents/                   # All agent files + scripts
└── vscode/                       # VS Code Copilot config
    ├── mcp.json
    └── settings-copilot.json     # Copilot-related settings only
```

**Restore process (documented in RESTORE.md):**
```powershell
# 1. Stop any running Copilot CLI sessions
# 2. Remove the current (broken) setup
Remove-Item "$env:USERPROFILE\.copilot" -Recurse -Force

# 3. Restore from backup
Copy-Item "<backup-path>\copilot" "$env:USERPROFILE\.copilot" -Recurse

# 4. Restore VS Code config (if backed up)
Copy-Item "<backup-path>\vscode\mcp.json" "$env:APPDATA\Code\User\mcp.json" -Force

# 5. Restore environment variables
$env:COPILOT_CUSTOM_INSTRUCTIONS_DIRS = ""  # or remove if wasn't set
[System.Environment]::SetEnvironmentVariable("COPILOT_CUSTOM_INSTRUCTIONS_DIRS", "", "User")

# 6. Verify — launch new Copilot CLI session, test persona switching
```

**Phase 0.5 Gate:**
- **Automated:** Script verifies backup directory exists, has all expected subdirectories, RESTORE.md present, file count matches source
- **UAT:** {{YOUR_NAME}} confirms backup exists and reviews RESTORE.md for clarity
- **{{YOUR_NAME}} confirms before proceeding to Phase 1**

---

### Phase 1: Local Refactor — 3-Layer Model on Work Machine
**Goal:** Refactor the existing local setup to use the 3-layer instruction model. Changes are committed to the repo incrementally.

> **Note:** Phases 1-3 reference `AGENTS.md` as the persona filename. These phases were completed before the rename to `persona.instructions.md` (see issue #72). The `AGENTS.md` references below are historically accurate for when the work was done.

| # | Todo | Description |
|---|------|-------------|
| 5 | **create-base-instructions** | Extract universal content from current copilot-instructions.md into a clean base layer (workspace, skills catalog, persona list, general behaviors) |
| 6 | **create-work-instance-rules** | Create Layer 2 instance rules for work machine (confidentiality, paths, WorkIQ) |
| 7 | **strip-persona-footers** | Remove the "Workspace & Tools Awareness" footer from all 7 persona files, rename to AGENTS.md. ✅ **COMPLETED (session 2026-03-01):** Verified all 7 AGENTS.md files match persona content exactly. Deleted all 7 redundant copilot-instructions.md files and 1 .bak file from security-architect. No unique content was lost — all Workspace & Tools sections were stale subsets of Layer 1. |
| 8 | **update-switch-script** | Update Switch-CopilotPersona.ps1 to copy into `personas/active/AGENTS.md` instead of overwriting copilot-instructions.md; add `-Target` parameter; **auto-detect new personas** — if a persona exists in the library but isn't listed in Layer 1 base instructions, automatically add it to the persona list in `copilot-instructions.md` |
| 9 | **set-env-var** | Set `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` pointing to `personas/active/` |
| 10 | **update-readme-phase1** | Update sync repo README with 3-layer architecture section including: layer-by-layer file path reference table (exact paths for editing each layer), what each layer controls and when it's loaded, how to edit each layer, persona switching how-to, and CHANGELOG entry |

**Phase 1 Gate:**
- **Automated test script (`test-phase1.ps1`):**
  - Verifies `copilot-instructions.md` exists and contains expected base content markers
  - Verifies `personas/active/.github/instructions/instance.instructions.md` exists
  - Verifies all 7 persona dirs have `AGENTS.md` (not `copilot-instructions.md`) — (Pre-verified: copilot-instructions.md files already removed)
  - Verifies no persona `AGENTS.md` contains "Workspace & Tools Awareness"
  - Verifies `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var is set correctly
  - Verifies `Switch-CopilotPersona.ps1` has `-Target` parameter
   - Verifies new persona auto-detection: creates a dummy persona dir, runs switch with `-List`, confirms dummy appears in Layer 1 base, cleans up
  - Verifies README.md has "3-Layer Architecture" and "Persona Switching" sections
  - Verifies CHANGELOG.md has Phase 1 entry
- **UAT steps for {{YOUR_NAME}}:**
  1. Launch new Copilot CLI session → run `/instructions` → verify 3 files loaded
  2. Ask: "What personas are available?" → verify answer comes from Layer 1
  3. Ask: "What are the confidentiality rules?" → verify answer comes from Layer 2
  4. Run `Switch-CopilotPersona.ps1 -Persona deep-technical` → verify Layer 3 changes, Layers 1+2 untouched
  5. Test 2-3 more persona switches → verify each works
  6. Create a new empty persona dir (`~/.copilot/personas/test-persona/AGENTS.md`), run switch with `-List` → verify "test-persona" now appears in the base instructions; clean up
  7. Do normal work for 15-30 minutes → note anything that feels different or broken
  8. File any issues found as GitHub Issues in `copilot-cli-config`
- **{{YOUR_NAME}} confirms before proceeding to Phase 2**

---

### Phase 2: Content Export to Repo
**Goal:** Export all content into the repo structure. Establish branch strategy.

| # | Todo | Description |
|---|------|-------------|
| 10 | **scaffold-repo-dirs** | Create full directory structure in the cloned repo (base/, personas/, skills/, agents/, scripts/, mcp/) |
| 11 | **create-instance-config-template** | Define instance-config.template.json schema |
| 12 | **create-base-template** | Create `base/copilot-instructions.md.template` with `{{variables}}` from the working Layer 1 |
| 13 | **export-personas** | Copy all 7 lean AGENTS.md personas into repo |
| 14 | **export-skills** | Copy all skills (SKILL.md + scripts + references, excluding __pycache__) |
| 15 | **export-agents** | Copy all agents + scripts |
| 16 | **export-scripts** | Copy utility scripts (New-CopilotProject, Switch-CopilotPersona) |
| 17 | **split-mcp-configs** | Create universal and work-specific MCP configs (CLI + VS Code formats) |
| 18 | **create-instance-rules** | Create work + personal instance rule files in `base/instance-rules/` |
| 19 | **update-readme-phase2** | Update sync repo README with repo structure section, what's included, branch strategy, and CHANGELOG entry |

**Phase 2 Gate:**
- **Automated test script (`test-phase2.ps1`):**
  - Verifies all expected directories exist in repo
  - Verifies all 7 persona AGENTS.md files are present and contain no workspace footer
  - Verifies all skill directories have SKILL.md
  - Verifies no `.gitignore`-listed files are tracked (config.json, sessions, etc.)
  - Verifies no obvious confidential patterns (scans for customer names, project-specific strings {{YOUR_NAME}} defines)
  - Verifies `copilot-instructions.md.template` uses `{{WORKSPACE_PATH}}` — no hardcoded OneDrive paths (e.g., `OneDrive - Microsoft`) in the template. The live `~/.copilot/copilot-instructions.md` will have the resolved path, but the repo template must not.
  - Verifies CHANGELOG.md has been updated
  - Verifies README.md has "Repo Structure" and "Branch Strategy" sections
- **UAT steps for {{YOUR_NAME}}:**
  1. Review the repo file tree — does it match the expected structure?
  2. Spot-check 2-3 persona AGENTS.md files — clean, role-only content?
  3. Spot-check 2-3 skills — SKILL.md + scripts intact?
  4. Review .gitignore — anything missing?
  5. Grep repo for any confidential terms you're concerned about
  6. Commit to `work` branch, create `main` from it, push to GitHub
  7. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 3**

---

### Phase 3: Init Script & VS Code Support
**Goal:** Build the initialization script that deploys from repo to a fresh `~/.copilot/`. Support both CLI and VS Code.

| # | Todo | Description |
|---|------|-------------|
| 19 | **build-init-script** | PowerShell init script: auto-detects CLI/VS Code, prompts for instance details, generates Layer 1 from template, deploys Layer 2, copies all content, sets env var |
| 20 | **vscode-deployment-path** | VS Code-specific deployment: instructions to user profile, mcp.json, ensure `chat.agentSkillsLocations` includes `~/.copilot/skills/` |
| 21 | **update-readme-phase3** | Update sync repo README with init script usage section, CLI vs VS Code deployment paths, and CHANGELOG entry |

**Phase 3 Gate:**
- **Automated test script (`test-phase3.ps1`):**
  - Verifies `init.ps1` runs without errors in dry-run mode
  - Verifies client detection logic (mock CLI-only, VS Code-only, both, neither)
  - Verifies template variable resolution produces valid files (no leftover `{{}}`)
  - Verifies generated `instance-config.json` matches schema
  - Verifies README.md has "Init Script" and "CLI vs VS Code" sections
  - Verifies CHANGELOG.md has Phase 3 entry
- **UAT steps for {{YOUR_NAME}}:**
  1. Run `init.ps1` in seed mode — verify it generates `instance-config.json` correctly
  2. Run `init.ps1` in consume simulation (backup ~/.copilot first, run in a temp dir) — verify all files deploy correctly
  3. Verify VS Code detection logic works on your machine (you have both CLI + VS Code)
  4. Push updated init script to repo; update CHANGELOG.md
  5. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 4**

**Phase 3 Learnings & Issues Fixed:**
- **Line endings (CRLF vs LF):** robocopy and git can produce files with different line endings. File comparison must use line-by-line (`Compare-Object` on `Get-Content`) instead of byte-level hashing (`Get-FileHash`). This avoids false "differs" on identical content. Applied to both `Get-FileStatus` and `Get-DirStatus`.
- **Directory comparison:** Comparing directories requires recursive file-by-file comparison, not just checking existence. The `Get-DirStatus` function was added. Path normalization (trailing backslash) is critical for `Substring` to produce matching relative paths.
- **Binary/empty files:** `Get-Content` returns null for some binary files (e.g., XSD schemas). Must wrap in `@()` and add `-ErrorAction SilentlyContinue` to prevent crashes.
- **Input validation:** All interactive menus must validate input in a loop — invalid characters should show an error and re-prompt, not silently accept as the default.
- **Compare workflow:** After showing a diff, the script must re-prompt with Import/Skip. The `while ($itemAction -eq "compare")` loop pattern handles this. Directory diffs should auto-show the SKILL.md/persona.instructions.md inline diff when those key files differ.
- **Existing config retention:** Init script should detect existing `instance-config.json` and offer to retain settings. If the user declines, each prompt should show the current value as the default.
- **Prompt clarity:** Prompts must always show valid options (e.g., "Options: work, personal") and the current default (e.g., "default: native"). Users pressing Enter with no input should always get a safe, sensible result.
- **Workspace paths:** Must resolve `~` to `$env:USERPROFILE` and store absolute paths. Display can show tilde but stored values must work in all PowerShell contexts.
- **Default environments:** Changed from "native,wsl,docker" to "native" only — most fresh setups won't have WSL/Docker.
- **Testing approach:** DryRun mode is essential for safe UAT. Synthetic diff testing (temporarily modifying local files, running DryRun, then reverting) is an effective UAT pattern for comparison logic.

---

### Phase 4: Config-Sync Skill
**Goal:** Build the skill that manages ongoing sync between machines.

| # | Todo | Description |
|---|------|-------------|
| 21 | **design-sync-skill** | Write SKILL.md with 5 workflows: check-for-updates, share-setup, promote-to-universal, sync-status, publish-template |
| 22 | **build-compare-script** | Python script computing diffs between local `~/.copilot/` and repo checkout |
| 23 | **build-sync-state-tracking** | Implement sync-state.json schema and management |
| 24 | **build-sanitize-script** | Python script for template repo sanitization (name/path replacement, voice profile blanking) |
| 25 | **install-sync-skill** | Deploy config-sync skill to local `~/.copilot/skills/config-sync/` |
| 26 | **update-readme-phase4** | Update sync repo README with config-sync workflows section, sync status how-to, and CHANGELOG entry |

**Phase 4 Gate:**
- **Automated test script (`test-phase4.ps1`):**
  - Verifies config-sync SKILL.md exists and has valid frontmatter
  - Verifies compare script runs without errors against current local vs repo
  - Verifies sync-state.json is created/updated correctly
  - Verifies sanitize script strips test name/path patterns correctly
  - Verifies README.md has "Config-Sync Workflows" and "Sync Status" sections
  - Verifies CHANGELOG.md has Phase 4 entry
- **UAT steps for {{YOUR_NAME}}:**
  1. Say "Check for updates" in Copilot CLI → verify skill triggers and shows accurate diff
  2. Say "What's my sync status?" → verify dashboard output
  3. Make a small local change (edit a persona) → say "Share my setup" → verify it detects the change
  4. Run sanitize script → review output for any personal data leakage
  5. Push sync skill to repo; update CHANGELOG.md
  6. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 5**

---

### Phase 5a: Peer Template — Basic Setup
**Goal:** A peer can fork the template, run init, and have a working Copilot environment. No update or contribution flow yet — just get started.

| # | Todo | Description |
|---|------|-------------|
| 26 | **create-template-init** | Peer-friendly `init.ps1` onboarding wizard: interactive import, backs up existing setup, auto-detects CLI/VS Code |
| 27 | **create-template-personas** | All 7 personas with `{{YOUR_NAME}}`/`{{WORKSPACE_PATH}}` and customization comments |
| 28 | **create-blank-voice-profile** | Blank voice-profile.md with build-your-own instructions |
| 29 | **run-initial-sanitize** | Run sanitization to populate template repo from private `main` |

**Phase 5a Gate:**
- **Automated test script (`test-phase5a.ps1`):**
  - Verifies no occurrence of "{{YOUR_NAME}}" or "{{YOUR_NAME}}banach" in template repo (only `{{YOUR_NAME}}`)
  - Verifies no specific workspace paths (only `{{WORKSPACE_PATH}}`)
  - Verifies voice-profile.md is blank template (not {{YOUR_NAME}}'s profile)
  - Verifies template `init.ps1` runs without errors in dry-run mode
  - Verifies CHANGELOG.md exists and has initial entry
- **UAT steps for {{YOUR_NAME}}:**
  1. Review the template repo — would this make sense to a peer who's never seen it?
  2. Simulate the full peer experience: fork → clone → run `init.ps1` in a temp directory
  3. Verify the init wizard asks the right questions and deploys correctly
  4. Check personas — do the customization comments clearly guide a new user?
  5. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 5b**

---

### Phase 5b: Peer Template — Update from Upstream
**Goal:** A peer who already set up from the template can pull improvements {{YOUR_NAME}} publishes later, with per-item review.

| # | Todo | Description |
|---|------|-------------|
| 30 | **build-template-update-skill** | Skill that checks upstream template for updates, shows categorized changes (new/updated/conflicts), lets peer choose incorporate/ignore/review for each item. Backs up before changes. |
| 31 | **document-upstream-setup** | Add instructions to template README for adding upstream remote and pulling updates |

**Phase 5b Gate:**
- **Automated test script (`test-phase5b.ps1`):**
  - Verifies template-update SKILL.md exists with valid frontmatter
  - Verifies the skill detects simulated upstream changes correctly
- **UAT steps for {{YOUR_NAME}}:**
  1. From the simulated peer fork, make a local customization (edit a persona)
  2. Publish a small change to the template repo (add a test file)
  3. Run the template-update skill — verify it shows the upstream change without overwriting the local customization
  4. Test incorporate, ignore, and review-diff options
  5. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 5c**

---

### Phase 5c: Peer Template — Contribute Back (Fork & PR)
**Goal:** Peers can contribute improvements back to the template repo via PRs, which {{YOUR_NAME}} reviews and optionally pulls up to his sync repo.

| # | Todo | Description |
|---|------|-------------|
| 32 | **document-contribution-guide** | Add CONTRIBUTING.md to template repo: how to fork, make improvements, submit PRs, what makes a good contribution |
| 33 | **document-pr-review-workflow** | Add instructions for {{YOUR_NAME}}: how to review peer PRs, merge to template, optionally pull improvements up to copilot-cli-config |

**Phase 5c Gate:**
- **Automated:** Verify CONTRIBUTING.md exists and references PR workflow
- **UAT steps for {{YOUR_NAME}}:**
  1. From the simulated peer fork, create a small improvement (e.g., improve a persona)
  2. Submit a PR to the template repo
  3. Review and merge the PR
  4. Verify the change is in the template repo
  5. Pull the improvement up to copilot-cli-config (manually for now)
  6. File any issues found
- **{{YOUR_NAME}} confirms before proceeding to Phase 6**

---

### Phase 6: Documentation Polish & Production Readiness
**Goal:** Final review and polish of all documentation built incrementally in Phases 0-5c. Stitch sections together, verify accuracy against what was actually built, test all prompts, ensure no stale references. This is NOT a from-scratch write — it's a production-readiness pass.

| # | Todo | Description |
|---|------|-------------|
| 38 | **finalize-private-readme** | Final review & polish of sync repo README: verify all sections from Phases 1-4 are accurate, cohesive, and complete; add "How To" index |
| 39 | **finalize-template-readme** | Final review & polish of template repo README: verify getting started, peer prompts, customization guide are accurate; add "How To" index |
| 40 | **finalize-starter-prompts** | Verify and test all four starter prompts: restore ({{YOUR_NAME}}/CLI), peer onboard (CLI), peer onboard (VS Code), sync check |
| 41 | **finalize-customization-guide** | Review and polish: how to create new personas, skills, agents, and instance rules from scratch |

**Phase 6 Gate:**
- **Automated test script (`test-phase6.ps1`):**
  - Verifies both READMEs exist and contain required sections: "How To", "Architecture", link to CHANGELOG.md
  - Verifies sync repo README references all 3 layers, branch strategy, and sync workflows
  - Verifies template repo README references both CLI and VS Code setup paths
  - Verifies all 4 starter prompts exist and contain no placeholder artifacts (no `{{}}` or `TODO`)
  - Verifies customization guide covers: personas, skills, agents, instance rules (section headers present)
  - Verifies CONTRIBUTING.md is linked from template README
  - Verifies CHANGELOG.md in both repos has entries for all phases
- **UAT steps for {{YOUR_NAME}}:**
  1. Read sync repo README end-to-end — is anything unclear, missing, or outdated vs. what was actually built?
  2. Read template repo README end-to-end — would a peer with no context understand how to get started?
  3. Copy-paste the "Restore my setup" prompt into a fresh Copilot CLI session — does it produce useful, accurate guidance?
  4. Copy-paste the "Peer CLI onboard" prompt — does it correctly describe the fork → init flow?
  5. Copy-paste the "Peer VS Code onboard" prompt — does it correctly describe the VS Code deployment path?
  6. Copy-paste the "Sync check" prompt — does it trigger the config-sync skill correctly?
  7. Follow the customization guide to create a brand-new test persona from scratch — does the guide actually work?
  8. Verify all CHANGELOG.md entries are accurate and complete
  9. File any remaining issues
- **{{YOUR_NAME}} confirms — project complete**

---

## CHANGELOG Convention

Both repos include a `CHANGELOG.md` at the root. Format:

```markdown
# Changelog

All notable changes to this configuration are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [YYYY-MM-DD] - Brief description
### Added
- New skill: config-sync for bidirectional sync between machines
### Changed
- Switched to 3-layer instruction model (base + instance + persona)
### Removed
- Removed duplicated workspace footer from persona files (Completed 2026-03-01)
```

The config-sync skill's push/publish workflows **automatically append** to CHANGELOG.md when committing changes. Each entry includes:
- Date
- What changed (added/changed/removed)
- Which files were affected

## GitHub Issue Templates

Both repos include issue templates in `.github/ISSUE_TEMPLATE/`:

### Bug Report (`bug-report.md`)
- What happened vs. what you expected
- Steps to reproduce
- Which phase/component is affected
- Environment (CLI/VS Code, OS, version)

### Feature Request (`feature-request.md`)
- What capability is missing
- Use case / why you need it
- Suggested approach (optional)

### UAT Feedback (`uat-feedback.md`)
- Which phase gate you're testing
- What worked well
- What didn't work or felt off
- Severity (blocking / annoying / cosmetic)

---

## Init Script: Interactive Import Workflow

The init script (both {{YOUR_NAME}}'s sync version and the peer template version) uses an **interactive, step-by-step import** process — not a bulk overwrite. Each component category is presented individually with options.

### Import Flow

```
┌─ Init Script Start ───────────────────────────────────┐
│                                                       │
│  1. Detect environment (CLI / VS Code / both)         │
│  2. Prompt: instance name, display name, paths        │
│  3. Check for existing ~/.copilot/ setup              │
│     └─ If exists: create timestamped backup           │
│                                                       │
│  For each component category:                         │
│  ┌──────────────────────────────────────────────┐     │
│  │  📁 Category: Personas (7 files)             │     │
│  │  ┌────────────────────────────────────────┐  │     │
│  │  │ productivity/persona.instructions.md                 │  │     │
│  │  │  Status: ⚠️ Exists locally (differs)   │  │     │
│  │  │  [Import] [Skip] [Compare] [Customize] │  │     │
│  │  └────────────────────────────────────────┘  │     │
│  │  ┌────────────────────────────────────────┐  │     │
│  │  │ deep-technical/persona.instructions.md               │  │     │
│  │  │  Status: ✅ New (doesn't exist locally) │  │     │
│  │  │  [Import] [Skip] [Customize]           │  │     │
│  │  └────────────────────────────────────────┘  │     │
│  │  ...                                         │     │
│  │  [Import All] [Skip All] [Review Each]       │     │
│  └──────────────────────────────────────────────┘     │
│                                                       │
│  Repeat for: Skills, Agents, Scripts, MCP, Base,      │
│              Instance Rules                           │
│                                                       │
│  4. Summary of what was imported/skipped              │
│  5. Set env var and finalize                          │
└───────────────────────────────────────────────────────┘
```

### Per-Item Options

| Option | Behavior |
|--------|----------|
| **Import** | Copy from repo to local, replacing existing (backup already made) |
| **Skip** | Keep local version, don't touch it |
| **Compare** | Show side-by-side diff of repo vs local version |
| **Customize** | Import, then open in editor for immediate customization |
| **Import All** | Accept all items in this category without reviewing |
| **Skip All** | Skip entire category |
| **Review Each** | Step through every item one at a time |

### Backup Before Replace

Before the import loop begins, the init script:
1. Detects if `~/.copilot/` already exists
2. If yes, creates a timestamped backup: `~/.copilot-backup-YYYY-MM-DD-HHMMSS/`
3. Logs what was backed up
4. The backup is a full copy — personas, skills, agents, scripts, instructions, config
5. At the end of init, the user is reminded the backup exists and can restore from it

```powershell
$backupPath = "$env:USERPROFILE\.copilot-backup-$(Get-Date -Format 'yyyy-MM-dd-HHmmss')"
if (Test-Path "$env:USERPROFILE\.copilot") {
    Copy-Item "$env:USERPROFILE\.copilot" $backupPath -Recurse
    Write-Host "Backed up existing setup to: $backupPath"
}
```

---

## Peer Template: Fork & Upstream Model

Peers don't just consume the template — they fork it and can contribute improvements back.

### Workflow

```
  {{YOUR_NAME}}'s Sync Repo                    {{YOUR_NAME}}'s Template Repo
  (copilot-cli-config)               (copilot-cli-starter)
  ┌──────────────┐                   ┌──────────────────┐
  │ main         │ ──sanitize──────> │ main             │
  │ work         │                   │                  │
  │ personal     │                   └────────┬─────────┘
  └──────────────┘                            │
                                        fork  │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                    │ Peer A's Fork│ │ Peer B's Fork│ │ Peer C's Fork│
                    │ (their own)  │ │ (their own)  │ │ (their own)  │
                    └──────┬───────┘ └──────┬───────┘ └──────────────┘
                           │                │
                      PR back to        PR back to
                      template          template
                           │                │
                           ▼                ▼
                    ┌──────────────────────────┐
                    │ {{YOUR_NAME}} reviews & merges PRs  │
                    │ → benefits all peers      │
                    │ → optionally pulls up to  │
                    │   copilot-cli-config      │
                    └──────────────────────────┘
```

### Peer Onboarding Guide (in template README)

1. **Fork** the `copilot-cli-starter` repo to your own GitHub account
2. **Clone** your fork locally
3. **Run `init.ps1`** — interactive wizard walks you through setup
4. **Customize** — edit personas, add skills, adjust instance rules
5. **Stay updated** — periodically pull from upstream (`copilot-cli-starter`) to get {{YOUR_NAME}}'s improvements

### Peer Update Workflow (Pull from Upstream)

When {{YOUR_NAME}} publishes improvements to the template repo, peers can pull them:

```powershell
# One-time: add upstream remote
git remote add upstream git@github.com:{{YOUR_NAME}}banach_microsoft/copilot-cli-starter.git

# Pull updates
git fetch upstream
git merge upstream/main --no-commit

# Review what changed
git diff --staged
```

But raw `git merge` is too blunt — the **template update skill** handles this intelligently:

### Template Update Skill (included in template repo)

When a peer says "Check for template updates", this skill:

1. Fetches latest from upstream (`copilot-cli-starter` main)
2. Compares upstream against local setup (similar to config-sync's compare logic)
3. Shows categorized changes:
   - **New in upstream** — new skills, personas, or agents {{YOUR_NAME}} added
   - **Updated in upstream** — files that changed since last pull
   - **Local customizations** — files the peer changed (would be overwritten by merge)
   - **No conflicts** — unchanged files on both sides
4. For each change, peer chooses: **Incorporate** / **Ignore** / **Review diff**
5. Handles merge conflicts by showing both versions and asking the peer to pick

### Peer → Template Contribution (PR Flow)

Peers who improve their setup can contribute back:

1. Peer pushes improvement to their fork
2. Peer creates a PR from their fork to `copilot-cli-starter`
3. {{YOUR_NAME}} reviews the PR — is it universally useful?
4. If yes: {{YOUR_NAME}} merges → all peers benefit on next upstream pull
5. If it's valuable enough: {{YOUR_NAME}} manually pulls the improvement into `copilot-cli-config` → it reaches his own sync setup

### Issue Replication Across Environments

When an issue is identified and fixed:

1. **Fix is made** in whichever environment discovered it ({{YOUR_NAME}}'s work, {{YOUR_NAME}}'s personal, or a peer's fork)
2. **Fix is committed** with a reference to the issue number
3. **Config-sync skill** ({{YOUR_NAME}}'s machines) or **template update skill** (peers) surfaces the fix as an available update on other machines/forks
4. **Each environment reviews and applies** the fix through their normal sync/update workflow — nothing is force-pushed

The issue templates include a field for "Environments affected" so fixes are tracked across all three tiers ({{YOUR_NAME}} sync → {{YOUR_NAME}} template → peer forks).

---

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo hosting | Two private repos under {{YOUR_NAME}}banach_microsoft | Both private; template shared via collaborator access to specific peers |
| Branch strategy | main/work/personal (sync repo), main only (template repo) | Clean separation with universal baseline |
| Peer sharing model | Private template repo + collaborator access | Internal audience only; peers fork and customize their own copy |
| Persona architecture | Native 3-layer model (base + instance rules + persona.instructions.md via COPILOT_CUSTOM_INSTRUCTIONS_DIRS) | Verified by testing; Copilot CLI loads all 3 natively; no assembly scripts needed |
| Confidentiality guardrail | Layer 2 (instance rules), not base | Work-specific rule; personal machine gets different Layer 2 content |
| Dual client support | CLI and VS Code deployment paths with auto-detection | Peers use whichever client they prefer; init script handles both |
| Template resolution | At init/sync time via instance-config.json | Files in ~/.copilot are always fully resolved; repo stores template + config |
| Sync mechanism | Copilot CLI skill (not a cron job or git hook) | Keeps {{YOUR_NAME}} in control; no surprises; works conversationally |
| Sanitization | Light touch (names/paths only) + manual review before publish | Internal audience; only truly confidential content needs scrubbing |
| Confidentiality | .gitignore + branch isolation + push-time warnings + copilot-instructions guardrail | Multiple layers; new guardrail in persona files catches cross-boundary leaks |
| Voice profile | Included in private repo; blank template in template repo | {{YOUR_NAME}}'s voice is personal; peers build their own |
| WorkIQ MCP | Work branch only in sync repo; referenced with setup instructions in template | Requires Microsoft authentication |
| Onboarding | Copy-paste prompts in README | Zero friction — paste a prompt, Copilot CLI walks you through setup |

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo hosting | Two private repos under {{YOUR_NAME}}banach_microsoft | Both private; template shared via collaborator access to specific peers |
| Branch strategy | main/work/personal (sync repo), main only (template repo) | Clean separation with universal baseline |
| Peer sharing model | Fork-based with upstream PRs | Peers fork template, customize freely, contribute improvements back via PRs |
| Persona architecture | Native 3-layer model (base + instance rules + persona.instructions.md via COPILOT_CUSTOM_INSTRUCTIONS_DIRS) | Verified by testing; Copilot CLI loads all 3 natively; no assembly scripts needed |
| Confidentiality guardrail | Layer 2 (instance rules), not base | Work-specific rule; personal machine gets different Layer 2 content |
| Dual client support | CLI and VS Code deployment paths with auto-detection | Peers use whichever client they prefer; init script handles both |
| Skills portability | Same SKILL.md format for CLI and VS Code (open standard) | No separate deployment needed; `~/.copilot/skills/` shared by both |
| Init script approach | Interactive, per-item import with backup | User controls what's imported; existing setup is backed up first; no silent overwrites |
| Template resolution | At init time via instance-config.json | Files in ~/.copilot are always fully resolved; repo stores templates with {{variables}} |
| Sync mechanism | Copilot CLI skill (not a cron job or git hook) | Keeps {{YOUR_NAME}} in control; no surprises; works conversationally |
| Sanitization | Light touch (names/paths only) + manual review before publish | Internal audience; only truly confidential content needs scrubbing |
| Voice profile | Included in private repo; blank template in template repo | {{YOUR_NAME}}'s voice is personal; peers build their own |
| WorkIQ MCP | Work branch only in sync repo; referenced with setup instructions in template | Requires Microsoft authentication |
| Onboarding | Copy-paste prompts in README | Zero friction — paste a prompt, Copilot CLI walks you through setup |
| Issue replication | Fixes flow through sync/update workflows, not force-pushed | Each environment reviews and applies fixes through normal channels |
| Changelog | Keep a Changelog format, auto-appended by sync/publish workflows | Every change is tracked; both repos have CHANGELOG.md |
| Diagrams | Mermaid format for all diagrams in READMEs | Renders natively on GitHub; no image files to maintain |
| README durability | Condensed structure trees (show patterns, not exhaustive lists); personas table always kept up to date | Avoids README churn when skills/agents are added/removed |

## Open Questions / Risks

1. **Skill file size** — docx, pptx, and xlsx skills contain large `office/schemas/` directories with XSD files (~100+ files each). Include them (needed for skills to work) but monitor repo size. Consider git LFS if it exceeds ~50MB.
2. **Personal GitHub access** — {{YOUR_NAME}}'s personal account needs collaborator access to the private repo. If org policies restrict this, host on the personal account instead and grant work access.
3. **Merge conflicts** — If both machines edit the same skill simultaneously, the sync skill needs a conflict resolution workflow. Initial version flags conflicts for manual resolution.
4. **Public repo licensing** — Decide what license to use for the public template (MIT recommended for maximum adoption).
5. **Skill licensing** — Some skills (docx, pdf, pptx, xlsx, skill-creator) include `LICENSE.txt` files. Verify these are compatible with public distribution.
6. **Template drift** — Over time, the public template may diverge significantly from {{YOUR_NAME}}'s private setup. The "publish template" workflow should show what's changed since the last publish so {{YOUR_NAME}} can keep it reasonably current.
7. **Multiple GitHub Accounts on one machine** - A machine may leverage more than one github account, one where GitHub copilot is used and another that handles syncs to a repository. The instance rules may need to account for this. 
---
name: environment-advisor
description: Evaluate whether a project should run on native Windows, WSL (Ubuntu), or Docker. Considers security risk, runtime conflicts, reproducibility needs, and productivity trade-offs. Use this when starting a new project, cloning an unfamiliar repo, or when the user mentions new technical work that may need isolation.
---

# Environment Advisor

When evaluating the right development environment, use this decision framework:

## Decision Matrix

| Factor | Native Windows ✅ | WSL (Ubuntu) 🐧 | Docker 🐳 |
|--------|-------------------|------------------|-----------|
| **Security** | Trusted internal code, M365 tools, PowerShell/Graph scripts | Untrusted open-source repos, pentest/security tools, credential sandboxing | Malware analysis, fully untrusted code, zero-trust execution |
| **Runtime** | Tools already installed (Node, Python, .NET), PowerShell-heavy work | Linux-only toolchains, different Python/Node versions than host, bash-native tools | Exact version pinning, complex multi-service stacks, CI parity needed |
| **Reproducibility** | Solo work, quick scripts, no hand-off needed | Partner hand-offs needing Linux env, GitHub Actions parity | Dockerfile-based reproducibility, team-shared dev environments |
| **Productivity** | OneDrive-synced content, M365 integration, GUI tools, Office files | CLI-heavy development, Linux-native workflows | Isolated microservices, database sandboxes, disposable environments |
| **Data Access** | Full OneDrive/Teams/Outlook access | OneDrive accessible via `/mnt/c/`, some friction | No direct OneDrive access, must mount volumes |

## Evaluation Process

### Step 1: Ask Key Questions
1. **What kind of work is this?** (content creation, coding, security research, automation)
2. **Are there untrusted dependencies?** (third-party repos, npm packages from unknown sources)
3. **Does it need specific runtimes?** (Python 3.12 when host has 3.11, Linux-only tools)
4. **Will this be shared/reproduced?** (partner hand-offs, CI/CD pipelines)
5. **Does it need M365/OneDrive integration?** (WorkIQ, Graph API, Office files)

### Step 2: Score & Recommend
- If ≥3 factors point to Native → recommend **Native Windows**
- If security or runtime factors point to isolation → recommend **WSL**
- If reproducibility + complex stack → recommend **Docker**
- If unsure, default to **Native Windows** (lowest friction)

### Step 3: Record the Decision
When used during project scaffolding, record in `project.json`:
```json
{
  "environment": "native|wsl|docker",
  "environment_reason": "Brief explanation of why this environment was chosen"
}
```

## Setup Helpers

### If WSL is recommended:
Run the helper script to bootstrap the project in WSL:
```powershell
& "$HOME\.copilot\skills\environment-advisor\setup-wsl-project.ps1" -ProjectName "<name>" -ProjectPath "<path>"
```

### If Docker is recommended:
- Offer to create a `Dockerfile` and `docker-compose.yml` in the project folder
- Suggest a base image appropriate for the project type
- Mount the project folder as a volume for file access

### If Native is recommended:
- Proceed with standard project creation in `CopilotWorkspace\`
- No additional setup needed

## Proactive Triggers
This skill should be invoked:
1. During `New-CopilotProject.ps1` execution
2. When the user mentions cloning an external/untrusted repo
3. When the user describes work requiring tools not installed on the host
4. When the user mentions security-sensitive work (pen testing, credential handling, malware analysis)

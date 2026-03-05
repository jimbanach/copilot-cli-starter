<#
.SYNOPSIS
    Create a new Copilot project in CopilotWorkspace.

.DESCRIPTION
    Scaffolds a new project folder in OneDrive CopilotWorkspace with:
    - .github/copilot-instructions.md (project-specific context)
    - project.json (metadata)
    - Optional git init

.PARAMETER Name
    Project name (used as folder name). Use kebab-case.

.PARAMETER Description
    Brief description of the project.

.PARAMETER Persona
    Which persona to associate with this project.

.PARAMETER Environment
    Development environment: native, wsl, or docker. If not specified, prompts for evaluation.

.EXAMPLE
    .\New-CopilotProject.ps1
    # Interactive mode — prompts for all details

.EXAMPLE
    .\New-CopilotProject.ps1 -Name "partner-workshop" -Persona "security-architect"
#>

param(
    [string]$Name,
    [string]$Description,
    [string]$Persona,
    [ValidateSet("native", "wsl", "docker", "")]
    [string]$Environment,
    [switch]$GitInit,
    [switch]$GitHub
)

$workspaceRoot = "$env:USERPROFILE\OneDrive - Microsoft\CopilotWorkspace"
$githubRoot = "$env:USERPROFILE\GitHubProjects"
$personaRoot = "$env:USERPROFILE\.copilot\personas"

# Check instance-config for custom paths
$instanceConfig = "$env:USERPROFILE\copilot-cli-config\instance-config.json"
if (-not (Test-Path $instanceConfig)) { $instanceConfig = "$env:USERPROFILE\GitHubProjects\copilot-cli-config\instance-config.json" }
if (Test-Path $instanceConfig) {
    $config = Get-Content $instanceConfig -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($config.workspace_path) { $workspaceRoot = $config.workspace_path }
    if ($config.github_projects_path) { $githubRoot = $config.github_projects_path }
}

# Ensure workspace exists
if (-not (Test-Path $workspaceRoot)) {
    New-Item -ItemType Directory -Path $workspaceRoot -Force | Out-Null
}

# Get available personas
$personas = Get-ChildItem -Path $personaRoot -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name

Write-Host ""
Write-Host "  ┌─────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "  │   New Copilot Project Wizard     │" -ForegroundColor Cyan
Write-Host "  └─────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# Prompt for name if not provided
if (-not $Name) {
    $Name = Read-Host "  Project name (kebab-case)"
    if (-not $Name) {
        Write-Host "  Project name is required." -ForegroundColor Red
        exit 1
    }
}

$projectPath = Join-Path $workspaceRoot $Name

if (Test-Path $projectPath) {
    Write-Host "  Project '$Name' already exists at $projectPath" -ForegroundColor Yellow
    exit 1
}

# Prompt for description if not provided
if (-not $Description) {
    $Description = Read-Host "  Brief description"
}

# Prompt for persona if not provided
if (-not $Persona) {
    Write-Host ""
    Write-Host "  Available personas:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $personas.Count; $i++) {
        # Read first line of persona file for description
        $personaFile = Join-Path $personaRoot "$($personas[$i])\copilot-instructions.md"
        $firstLine = ""
        if (Test-Path $personaFile) {
            $firstLine = (Get-Content $personaFile -TotalCount 1) -replace "^# Persona: ", ""
        }
        Write-Host "  [$($i + 1)] $($personas[$i]) — $firstLine"
    }
    Write-Host ""
    $selection = Read-Host "  Select persona (1-$($personas.Count))"
    if ($selection -match '^\d+$' -and [int]$selection -ge 1 -and [int]$selection -le $personas.Count) {
        $Persona = $personas[[int]$selection - 1]
    } else {
        Write-Host "  Invalid selection. Using 'productivity' as default." -ForegroundColor Yellow
        $Persona = "productivity"
    }
}

# Prompt for environment if not provided
if (-not $Environment) {
    Write-Host ""
    Write-Host "  Development environment:" -ForegroundColor Cyan
    Write-Host "  [1] native  — Windows workstation (OneDrive, M365, PowerShell)"
    Write-Host "  [2] wsl     — WSL Ubuntu (Linux isolation, CLI-heavy work)"
    Write-Host "  [3] docker  — Docker container (full isolation, reproducible)"
    Write-Host ""
    Write-Host "  Tip: Use the /environment-advisor skill in Copilot for a detailed recommendation." -ForegroundColor DarkGray
    Write-Host ""
    $envSelection = Read-Host "  Select environment (1-3, default: 1)"
    switch ($envSelection) {
        "2" { $Environment = "wsl" }
        "3" { $Environment = "docker" }
        default { $Environment = "native" }
    }
}

# --- GitHub-backed project handling ---
if (-not $GitHub) {
    Write-Host ""
    Write-Host "  Will this project be backed by a GitHub repository?" -ForegroundColor Cyan
    $ghChoice = Read-Host "  GitHub-backed? (y/N, default: N)"
    if ($ghChoice -match '^[Yy]') { $GitHub = $true }
}

if ($GitHub) {
    # GitHub projects go to GitHubProjects folder, not OneDrive
    New-Item -ItemType Directory -Path $githubRoot -Force | Out-Null
    $projectPath = Join-Path $githubRoot $Name

    if (Test-Path $projectPath) {
        Write-Host "  Project '$Name' already exists at $projectPath" -ForegroundColor Yellow
        exit 1
    }

    Write-Host ""
    Write-Host "  ℹ️  GitHub-backed projects are stored in: $githubRoot" -ForegroundColor Cyan
    Write-Host "  A shortcut will be created in CopilotWorkspace for easy access." -ForegroundColor DarkGray
} else {
    $projectPath = Join-Path $workspaceRoot $Name

    if (Test-Path $projectPath) {
        Write-Host "  Project '$Name' already exists at $projectPath" -ForegroundColor Yellow
        exit 1
    }

    # Warn if user somehow specified a cloud-sync path with GitInit
    if ($GitInit) {
        $cloudSyncPatterns = @('OneDrive', 'Dropbox', 'Google Drive', 'iCloud')
        foreach ($pattern in $cloudSyncPatterns) {
            if ($projectPath -match [regex]::Escape($pattern)) {
                Write-Host ""
                Write-Host "  ⚠️  WARNING: You're creating a git repo inside a cloud-sync folder ($pattern)." -ForegroundColor Red
                Write-Host "  This can cause sync conflicts. Consider using -GitHub flag instead." -ForegroundColor Red
                $proceed = Read-Host "  Continue anyway? (y/N, default: N)"
                if ($proceed -notmatch '^[Yy]') {
                    Write-Host "  Cancelled. Re-run with -GitHub flag." -ForegroundColor Yellow
                    exit 0
                }
                break
            }
        }
    }
}

# Create project structure
Write-Host ""
Write-Host "  Creating project..." -ForegroundColor Cyan

if ($Environment -eq "wsl" -and -not $GitHub) {
    # Delegate non-GitHub WSL projects to WSL setup script
    $setupScript = "$env:USERPROFILE\.copilot\skills\environment-advisor\setup-wsl-project.ps1"
    if (Test-Path $setupScript) {
        & $setupScript -ProjectName $Name
    } else {
        Write-Host "  WSL setup script not found. Creating in CopilotWorkspace instead." -ForegroundColor Yellow
        $Environment = "native"
    }
}

if ($Environment -eq "wsl" -and $GitHub) {
    # GitHub-backed WSL projects: create in GitHubProjects (Windows-accessible)
    # and fall through to standard GitHub project creation
    Write-Host "  ℹ️  GitHub-backed WSL project — creating in $githubRoot (Windows-accessible)" -ForegroundColor Cyan
    Write-Host "  Access from WSL via: /mnt/c/Users/$env:USERNAME/GitHubProjects/$Name" -ForegroundColor DarkGray
}

if ($Environment -ne "wsl" -or $GitHub) {
    # Create native or docker project in CopilotWorkspace
    New-Item -ItemType Directory -Path "$projectPath\.github" -Force | Out-Null

    # Create project-specific copilot-instructions.md
    $instructions = @"
# Project: $Name

## Description
$Description

## Persona
This project uses the **$Persona** persona.

## Environment
- **Type**: $Environment
- **Workspace**: $projectPath

## Context
[Add project-specific instructions, goals, key stakeholders, and reference links here]

## Key Resources
- Shared resources: ``CopilotWorkspace\_shared-resources\``
- Project metadata: ``project.json``
"@
    Set-Content -Path "$projectPath\.github\copilot-instructions.md" -Value $instructions

    # Create project.json
    $projectMeta = @{
        name = $Name
        description = $Description
        persona = $Persona
        environment = $Environment
        environment_reason = ""
        status = "active"
        created = (Get-Date -Format "yyyy-MM-dd")
        tags = @()
        github_backed = $GitHub.IsPresent
        storage_path = $projectPath
    } | ConvertTo-Json -Depth 3
    Set-Content -Path "$projectPath\project.json" -Value $projectMeta

    # Create a starter README
    Set-Content -Path "$projectPath\README.md" -Value "# $Name`n`n$Description`n"

    # Docker setup if needed
    if ($Environment -eq "docker") {
        $dockerfile = @"
FROM mcr.microsoft.com/devcontainers/base:ubuntu
WORKDIR /workspace
COPY . .
"@
        Set-Content -Path "$projectPath\Dockerfile" -Value $dockerfile
    }

    # Git init for GitHub projects (always) or if requested
    if ($GitHub -or $GitInit) {
        Push-Location $projectPath
        git init --quiet
        Pop-Location
    }

    # Create forwarding folder in CopilotWorkspace for GitHub-backed projects
    if ($GitHub) {
        $forwardingPath = Join-Path $workspaceRoot $Name
        New-Item -ItemType Directory -Path "$forwardingPath\.github" -Force | Out-Null

        # Forwarding project.json
        $fwdMeta = @{
            name = $Name
            description = $Description
            github_backed = $true
            moved_to = $projectPath
            status = "active"
            note = "This project lives in $projectPath. This folder is a forwarding reference."
        } | ConvertTo-Json -Depth 3
        Set-Content -Path "$forwardingPath\project.json" -Value $fwdMeta

        # MOVED-TO-GITHUB.md
        $movedMd = @"
# $Name — Moved to GitHub

This project is backed by a GitHub repository and has been moved to:

**$projectPath**

## Why?
Git repositories should not live inside cloud-sync folders (like OneDrive) because it causes sync conflicts and unreliable state. GitHub-backed projects are stored in the dedicated GitHub folder.

## How to access
- **File Explorer:** Use the shortcut ``$Name.lnk`` in this folder
- **Terminal:** ``cd $projectPath``
- **Copilot CLI:** Copilot will automatically redirect to the correct location
"@
        Set-Content -Path "$forwardingPath\MOVED-TO-GITHUB.md" -Value $movedMd

        # Forwarding copilot-instructions.md
        $fwdInstructions = @"
# Project: $Name (Forwarding Reference)

**This project has moved to ``$projectPath``.**

Do NOT work in this folder. Automatically ``cd`` to the actual project location before proceeding:
``cd $projectPath``
"@
        Set-Content -Path "$forwardingPath\.github\copilot-instructions.md" -Value $fwdInstructions

        # .lnk shortcut for File Explorer
        $shortcutPath = Join-Path $forwardingPath "$Name.lnk"
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $projectPath
        $shortcut.Description = "$Name (GitHub-backed — stored in $githubRoot)"
        $shortcut.Save()

        Write-Host "  📁 Forwarding folder created in CopilotWorkspace" -ForegroundColor DarkGray
    }
}

# Create WSL symlink for GitHub-backed WSL projects
if ($Environment -eq "wsl" -and $GitHub) {
    $wslProjectPath = "/mnt/c" + ($projectPath -replace '^C:', '' -replace '\\', '/')
    $wslLinkDir = "~/projects"
    $wslLinkPath = "$wslLinkDir/$Name"

    # Find a usable WSL distro (skip docker-desktop distros)
    $wslDistro = $null
    $distros = wsl --list --quiet 2>$null | ForEach-Object { ($_ -replace '[^\x20-\x7E]', '').Trim() } | Where-Object { $_ -and $_ -notlike '*docker*' }
    if ($distros) { $wslDistro = ($distros | Select-Object -First 1).Trim() }

    Write-Host ""
    Write-Host "  🔗 Creating WSL symlink..." -ForegroundColor Cyan
    try {
        if ($wslDistro) {
            wsl -d $wslDistro -- bash -c "mkdir -p $wslLinkDir && ln -sfn '$wslProjectPath' '$wslLinkPath'" 2>&1 | Out-Null
            Write-Host "  ✅ WSL symlink: ~/projects/$Name → $wslProjectPath (distro: $wslDistro)" -ForegroundColor DarkGray
        } else {
            Write-Host "  ⚠️  No usable WSL distro found. Create symlink manually:" -ForegroundColor Yellow
            Write-Host "    ln -s $wslProjectPath ~/projects/$Name" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "  ⚠️  Could not create WSL symlink. Create manually:" -ForegroundColor Yellow
        Write-Host "    ln -s $wslProjectPath ~/projects/$Name" -ForegroundColor DarkGray
    }
}

# Summary
Write-Host ""
Write-Host "  ✅ Project '$Name' created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  📁 Location:    $projectPath" -ForegroundColor DarkGray
Write-Host "  🎭 Persona:     $Persona" -ForegroundColor DarkGray
Write-Host "  🖥  Environment: $Environment" -ForegroundColor DarkGray
if ($GitHub) {
    Write-Host "  🔗 GitHub:      Yes (stored in $githubRoot)" -ForegroundColor DarkGray
    Write-Host "  📁 Forwarding:  $workspaceRoot\$Name\" -ForegroundColor DarkGray
}
if ($Environment -eq "wsl" -and $GitHub) {
    Write-Host "  🐧 WSL path:    ~/projects/$Name" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "  • cd to the project folder and start Copilot CLI"
Write-Host "  • Edit .github\copilot-instructions.md to add project context"
if ($GitHub) {
    Write-Host "  • Create a GitHub repo: gh repo create $Name --private"
    Write-Host "  • Push initial commit: git add -A && git commit -m 'Initial project' && git push -u origin main"
}
Write-Host "  • Use /skills list to see available skills"
Write-Host ""

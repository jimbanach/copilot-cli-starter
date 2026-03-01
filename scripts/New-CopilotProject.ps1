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
    [switch]$GitInit
)

$workspaceRoot = "$env:USERPROFILE\OneDrive - Microsoft\CopilotWorkspace"
$personaRoot = "$env:USERPROFILE\.copilot\personas"

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

# Create project structure
Write-Host ""
Write-Host "  Creating project..." -ForegroundColor Cyan

if ($Environment -eq "wsl") {
    # Delegate to WSL setup script
    $setupScript = "$env:USERPROFILE\.copilot\skills\environment-advisor\setup-wsl-project.ps1"
    if (Test-Path $setupScript) {
        & $setupScript -ProjectName $Name
    } else {
        Write-Host "  WSL setup script not found. Creating in CopilotWorkspace instead." -ForegroundColor Yellow
        $Environment = "native"
    }
}

if ($Environment -ne "wsl") {
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

    # Git init if requested
    if ($GitInit) {
        Push-Location $projectPath
        git init --quiet
        Pop-Location
    }
}

# Summary
Write-Host ""
Write-Host "  ✅ Project '$Name' created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  📁 Location:    $projectPath" -ForegroundColor DarkGray
Write-Host "  🎭 Persona:     $Persona" -ForegroundColor DarkGray
Write-Host "  🖥  Environment: $Environment" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "  • cd to the project folder and start Copilot CLI"
Write-Host "  • Edit .github\copilot-instructions.md to add project context"
Write-Host "  • Use /skills list to see available skills"
Write-Host ""

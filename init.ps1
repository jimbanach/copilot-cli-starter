<#
.SYNOPSIS
    Initialize Copilot CLI environment from the copilot-cli-config repo.

.DESCRIPTION
    Deploys the 3-layer instruction model, personas, skills, agents, scripts,
    and MCP configs from the repo to ~/.copilot/. Supports both Copilot CLI
    and VS Code deployments with auto-detection.

    Modes:
    - Seed: Export current local setup INTO the repo (first-time on source machine)
    - Consume: Deploy FROM the repo to a fresh ~/.copilot/ (new machine setup)

.PARAMETER Mode
    'seed' or 'consume'. If not provided, auto-detects based on repo content.

.PARAMETER DryRun
    Show what would be done without making changes.

.EXAMPLE
    .\init.ps1                    # Auto-detect mode
    .\init.ps1 -Mode consume      # Deploy from repo to local
    .\init.ps1 -DryRun            # Preview without changes
#>

param(
    [ValidateSet("seed", "consume", "")]
    [string]$Mode = "",
    [switch]$DryRun
)

# ============================================================
# Configuration
# ============================================================
$repoRoot = $PSScriptRoot
$copilotDir = "$env:USERPROFILE\.copilot"
$templateFile = "$repoRoot\base\copilot-instructions.md.template"
$instanceConfigTemplate = "$repoRoot\instance-config.template.json"

# Component categories and their repo/local paths
$categories = @(
    @{ Name = "Personas"; RepoPath = "personas"; LocalPath = "personas"; Pattern = "*/AGENTS.md"; Description = "Role-specific persona files" }
    @{ Name = "Skills";   RepoPath = "skills";   LocalPath = "skills";   Pattern = "*/SKILL.md";  Description = "Portable skills (CLI + VS Code)" }
    @{ Name = "Agents";   RepoPath = "agents";   LocalPath = "agents";   Pattern = "*.agent.md";  Description = "Custom agent profiles" }
    @{ Name = "Scripts";  RepoPath = "scripts";  LocalPath = ".";        Pattern = "*.ps1";       Description = "Utility scripts" }
)

# ============================================================
# Helper Functions
# ============================================================

function Write-Banner {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "  ┌$('─' * ($Text.Length + 4))┐" -ForegroundColor $Color
    Write-Host "  │  $Text  │" -ForegroundColor $Color
    Write-Host "  └$('─' * ($Text.Length + 4))┘" -ForegroundColor $Color
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host "  → $Text" -ForegroundColor White
}

function Write-Success {
    param([string]$Text)
    Write-Host "  ✅ $Text" -ForegroundColor Green
}

function Write-Skip {
    param([string]$Text)
    Write-Host "  ⏭️  $Text" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Text)
    Write-Host "  ℹ️  $Text" -ForegroundColor DarkGray
}

function Detect-Clients {
    $clients = @()
    if (Test-Path "$copilotDir\config.json") { $clients += "cli" }
    if (Test-Path "$env:APPDATA\Code\User\settings.json") { $clients += "vscode" }
    if (Test-Path "$env:APPDATA\Code - Insiders\User\settings.json") { $clients += "vscode-insiders" }
    return $clients
}

function Get-FileStatus {
    param([string]$RepoFile, [string]$LocalFile)
    if (-not (Test-Path $LocalFile)) { return "new" }
    # Compare line-by-line to ignore line-ending differences (CRLF vs LF)
    $repoLines = Get-Content $RepoFile
    $localLines = Get-Content $LocalFile
    $diff = Compare-Object $repoLines $localLines
    if ($diff.Count -eq 0) { return "identical" }
    return "differs"
}

function Get-DirStatus {
    param([string]$RepoDir, [string]$LocalDir)
    if (-not (Test-Path $LocalDir)) { return "new" }

    # Normalize paths to end with backslash for consistent Substring
    $repoDirN = $RepoDir.TrimEnd('\') + '\'
    $localDirN = $LocalDir.TrimEnd('\') + '\'

    # Compare all files recursively (excluding __pycache__ and .pyc)
    $repoFiles = @(Get-ChildItem $RepoDir -Recurse -File | Where-Object {
        $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc'
    } | ForEach-Object { @{ Rel = $_.FullName.Substring($repoDirN.Length); Path = $_.FullName } })

    $localFiles = @(Get-ChildItem $LocalDir -Recurse -File | Where-Object {
        $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc'
    } | ForEach-Object { @{ Rel = $_.FullName.Substring($localDirN.Length); Path = $_.FullName } })

    # Compare file counts
    if ($repoFiles.Count -ne $localFiles.Count) { return "differs" }

    # Compare each file by relative path and content (line-by-line to ignore line endings)
    $repoLookup = @{}
    foreach ($f in $repoFiles) { $repoLookup[$f.Rel] = $f.Path }
    foreach ($f in $localFiles) {
        if (-not $repoLookup.ContainsKey($f.Rel)) { return "differs" }
        $repoContent = @(Get-Content $repoLookup[$f.Rel] -ErrorAction SilentlyContinue)
        $localContent = @(Get-Content $f.Path -ErrorAction SilentlyContinue)
        if ($repoContent.Count -ne $localContent.Count) { return "differs" }
        if ($repoContent.Count -gt 0 -and $localContent.Count -gt 0) {
            $diff = Compare-Object $repoContent $localContent
            if ($diff.Count -gt 0) { return "differs" }
        }
    }
    return "identical"
}

function Show-CategoryMenu {
    param([string]$CategoryName, [int]$NewCount, [int]$DiffersCount, [int]$IdenticalCount)

    $total = $NewCount + $DiffersCount + $IdenticalCount
    Write-Host ""
    Write-Host "  📁 $CategoryName ($total items)" -ForegroundColor Cyan
    if ($NewCount -gt 0) { Write-Host "     $NewCount new" -ForegroundColor Green }
    if ($DiffersCount -gt 0) { Write-Host "     $DiffersCount changed" -ForegroundColor Yellow }
    if ($IdenticalCount -gt 0) { Write-Host "     $IdenticalCount identical" -ForegroundColor DarkGray }
    Write-Host ""

    if ($IdenticalCount -eq $total) {
        Write-Info "All items identical — nothing to do"
        return "skip-all"
    }

    while ($true) {
        Write-Host "  [1] Import All — accept all new and changed items"
        Write-Host "  [2] Skip All — keep local versions, skip this category"
        Write-Host "  [3] Review Each — step through items one at a time"
        Write-Host ""
        $choice = Read-Host "  Select (1-3, default: 1)"

        if ($choice -eq "" -or $choice -eq "1") { return "import-all" }
        if ($choice -eq "2") { return "skip-all" }
        if ($choice -eq "3") { return "review-each" }
        Write-Host "  ⚠️  Invalid input — please enter 1, 2, or 3" -ForegroundColor Red
    }
}

function Show-ItemMenu {
    param([string]$ItemName, [string]$Status)

    $statusIcon = switch ($Status) {
        "new" { "🆕 New (doesn't exist locally)" }
        "differs" { "⚠️  Changed (differs from local)" }
        "identical" { "✅ Identical" }
    }

    Write-Host "    $ItemName — $statusIcon"

    if ($Status -eq "identical") { return "skip" }

    while ($true) {
        Write-Host "    [1] Import  [2] Skip  [3] Compare"
        $choice = Read-Host "    Select (1-3, default: 1)"

        if ($choice -eq "" -or $choice -eq "1") { return "import" }
        if ($choice -eq "2") { return "skip" }
        if ($choice -eq "3") { return "compare" }
        Write-Host "    ⚠️  Invalid input — please enter 1, 2, or 3" -ForegroundColor Red
    }
}

function Resolve-Template {
    param([string]$TemplatePath, [hashtable]$Variables)
    $content = Get-Content $TemplatePath -Raw
    foreach ($key in $Variables.Keys) {
        $content = $content -replace "\{\{$key\}\}", $Variables[$key]
    }
    return $content
}

# ============================================================
# Main Script
# ============================================================

Write-Banner "Copilot CLI Config — Initialization"

# --- Prerequisites check ---
Write-Step "Checking prerequisites..."
$prereqFail = $false

# Git
$gitVersion = git --version 2>$null
if ($gitVersion) { Write-Success "git: $gitVersion" }
else { Write-Host "  ❌ git not found — install from https://git-scm.com/downloads" -ForegroundColor Red; $prereqFail = $true }

# GitHub CLI
$ghVersion = gh --version 2>$null | Select-Object -First 1
if ($ghVersion) { Write-Success "gh: $ghVersion" }
else { Write-Host "  ❌ gh CLI not found — install from https://cli.github.com/" -ForegroundColor Red; $prereqFail = $true }

# Python
$pyVersion = python --version 2>$null
if ($pyVersion) { Write-Success "python: $pyVersion" }
else { Write-Host "  ❌ python not found — install from https://www.python.org/downloads/" -ForegroundColor Red; $prereqFail = $true }

# PowerShell version
if ($PSVersionTable.PSVersion.Major -ge 6) { Write-Success "PowerShell: $($PSVersionTable.PSVersion)" }
else { Write-Host "  ⚠️  PowerShell $($PSVersionTable.PSVersion) — version 6+ recommended. Install from https://learn.microsoft.com/powershell/scripting/install/installing-powershell" -ForegroundColor Yellow }

# Node.js (optional — needed for MCP servers)
$nodeVersion = node --version 2>$null
if ($nodeVersion) { Write-Success "node: $nodeVersion" }
else { Write-Host "  ⚠️  node.js not found (optional — needed for MCP servers like Playwright). Install from https://nodejs.org/" -ForegroundColor Yellow }

if ($prereqFail) {
    Write-Host ""
    Write-Host "  Install the missing prerequisites above, then re-run init.ps1" -ForegroundColor Red
    exit 1
}

# --- Step 0: Verify GitHub account ---
Write-Step "Checking GitHub authentication..."
$ghAccount = gh api user --jq '.login' 2>$null
if ($ghAccount) {
    Write-Host "  Active GitHub account: $ghAccount" -ForegroundColor White
    $confirmAccount = Read-Host "  Is this the correct account for this setup? (Y/n, default: Y)"
    if ($confirmAccount -match '^[Nn]') {
        Write-Host ""
        Write-Host "  Switch accounts with: gh auth switch" -ForegroundColor Yellow
        Write-Host "  Or add a new account: gh auth login --web" -ForegroundColor Yellow
        Write-Host "  Then re-run init.ps1" -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Host "  ⚠️  Not authenticated with GitHub CLI." -ForegroundColor Yellow
    Write-Host "  Run: gh auth login --web" -ForegroundColor Yellow
    Write-Host "  Then re-run init.ps1" -ForegroundColor Yellow
    exit 1
}

# --- Step 1: Detect clients ---
Write-Step "Detecting Copilot clients..."
$clients = Detect-Clients
if ($clients.Count -eq 0) {
    Write-Host "  No Copilot CLI or VS Code detected." -ForegroundColor Yellow
    Write-Host "  Will configure for CLI by default." -ForegroundColor Yellow
    $clients = @("cli")
} else {
    Write-Success "Detected: $($clients -join ', ')"
}

# --- Step 2: Auto-detect or confirm mode ---
if (-not $Mode) {
    $hasPersonas = (Get-ChildItem "$repoRoot\personas" -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path "$($_.FullName)\AGENTS.md" }).Count -gt 0

    if ($hasPersonas) {
        $Mode = "consume"
        Write-Info "Repo has content — defaulting to 'consume' mode (deploy from repo to local)"
    } else {
        $Mode = "seed"
        Write-Info "Repo is empty — defaulting to 'seed' mode (export local to repo)"
    }
}
Write-Step "Mode: $Mode"

# --- Step 3: Prompt for instance details ---
Write-Host ""
Write-Host "  Instance Configuration" -ForegroundColor Cyan
Write-Host "  ─────────────────────" -ForegroundColor Cyan

# Check for existing instance config
$existingConfig = $null
$configPath = "$repoRoot\instance-config.json"
if (Test-Path $configPath) {
    $existingConfig = Get-Content $configPath -Raw | ConvertFrom-Json
    Write-Host ""
    Write-Host "  Existing configuration found:" -ForegroundColor Green
    Write-Host "    Instance:     $($existingConfig.instance_name)" -ForegroundColor DarkGray
    Write-Host "    Display name: $($existingConfig.user_display_name)" -ForegroundColor DarkGray
    Write-Host "    Workspace:    $($existingConfig.workspace_path)" -ForegroundColor DarkGray
    Write-Host "    GitHub:       $($existingConfig.github_account)" -ForegroundColor DarkGray
    Write-Host "    Environments: $($existingConfig.available_environments -join ', ')" -ForegroundColor DarkGray
    Write-Host "    MCP profile:  $($existingConfig.mcp_profile)" -ForegroundColor DarkGray
    Write-Host ""

    $keepExisting = Read-Host "  Keep these settings? (Y/n, default: Y)"
    if ($keepExisting -eq "" -or $keepExisting -match '^[Yy]') {
        $instanceName = $existingConfig.instance_name
        $displayName = $existingConfig.user_display_name
        $workspacePath = $existingConfig.workspace_path
        $githubProjectsPath = if ($existingConfig.github_projects_path) { $existingConfig.github_projects_path } else { "$env:USERPROFILE\GitHubProjects" }
        $githubAccount = $existingConfig.github_account
        $environments = @($existingConfig.available_environments)
        $mcpProfile = $existingConfig.mcp_profile
        Write-Success "Retained existing configuration"
    } else {
        $existingConfig = $existingConfig  # keep as defaults for prompts below
    }
}

# Prompt for settings (skip if retained from existing config)
if (-not $instanceName) {
    # Use existing values as defaults, or fall back to sensible defaults
    $defInstance = if ($existingConfig) { $existingConfig.instance_name } else { "work" }
    Write-Host ""
    Write-Host "  Options: work, personal" -ForegroundColor DarkGray
    $instanceName = Read-Host "  Instance name (default: $defInstance)"
    if (-not $instanceName) { $instanceName = $defInstance }

    $defDisplay = if ($existingConfig) { $existingConfig.user_display_name } else { $env:USERNAME }
    $displayName = Read-Host "  Your display name (default: $defDisplay)"
    if (-not $displayName) { $displayName = $defDisplay }

    $defWorkspace = if ($existingConfig) { $existingConfig.workspace_path }
        elseif ($instanceName -eq "work") { "$env:USERPROFILE\OneDrive - Microsoft\CopilotWorkspace" }
        else { "$env:USERPROFILE\CopilotWorkspace" }
    $workspacePath = Read-Host "  Workspace path (default: $defWorkspace)"
    if (-not $workspacePath) { $workspacePath = $defWorkspace }
    $workspacePath = $workspacePath -replace '^~', $env:USERPROFILE

    $defGithub = if ($existingConfig) { $existingConfig.github_account } else { (gh api user --jq '.login' 2>$null) }
    $githubAccount = Read-Host "  GitHub account username (default: $defGithub)"
    if (-not $githubAccount) { $githubAccount = $defGithub }

    $defEnv = if ($existingConfig) { $existingConfig.available_environments -join ', ' } else { "native" }
    Write-Host "  Options: native, wsl, docker (comma-separated)" -ForegroundColor DarkGray
    $envChoices = Read-Host "  Available environments (default: $defEnv)"
    if (-not $envChoices) { $envChoices = $defEnv }
    $environments = @(($envChoices -split ',').Trim())

    $defGhProjects = if ($existingConfig.github_projects_path) { $existingConfig.github_projects_path } else { "$env:USERPROFILE\GitHubProjects" }
    $githubProjectsPath = Read-Host "  GitHub projects folder (default: $defGhProjects)"
    if (-not $githubProjectsPath) { $githubProjectsPath = $defGhProjects }
    $githubProjectsPath = $githubProjectsPath -replace '^~', $env:USERPROFILE

    $mcpProfile = if ($instanceName -eq "work") { "work" } else { "universal" }
}

# --- Step 3b: Auto-detect known folder paths (OneDrive Known Folder Move) ---
$knownFolders = @{
    desktop = [Environment]::GetFolderPath('Desktop')
    documents = [Environment]::GetFolderPath('MyDocuments')
}
$kfmDetected = ($knownFolders.desktop -ne "$env:USERPROFILE\Desktop") -or ($knownFolders.documents -ne "$env:USERPROFILE\Documents")
if ($kfmDetected) {
    Write-Info "OneDrive Known Folder Move detected:"
    Write-Info "  Desktop:   $($knownFolders.desktop)"
    Write-Info "  Documents: $($knownFolders.documents)"
} else {
    Write-Info "Known folders at default profile paths"
}

# --- Step 4: Create instance-config.json ---
$instanceConfig = @{
    instance_name = $instanceName
    user_display_name = $displayName
    workspace_path = $workspacePath
    github_projects_path = $githubProjectsPath
    github_account = $githubAccount
    available_environments = $environments
    mcp_profile = $mcpProfile
    repo_local_path = $repoRoot
    branch = if ($instanceName -eq "work") { "work" } elseif ($instanceName -eq "personal") { "personal" } else { "main" }
    known_folders = $knownFolders
}

$configPath = "$repoRoot\instance-config.json"
if ($DryRun) {
    Write-Info "[DRY RUN] Would create instance-config.json"
} else {
    $instanceConfig | ConvertTo-Json -Depth 3 | Set-Content $configPath
    Write-Success "Created instance-config.json"
}

# --- Step 5: Backup existing setup ---
$backupRoot = "$env:USERPROFILE\.copilot-backups"
$maxBackups = 3

if ((Test-Path $copilotDir) -and $Mode -eq "consume") {
    $backupPath = "$backupRoot\$(Get-Date -Format 'yyyy-MM-dd-HHmmss')"
    Write-Step "Existing ~/.copilot/ found — creating backup..."
    if ($DryRun) {
        Write-Info "[DRY RUN] Would backup to $backupPath"
    } else {
        $excludeDirs = @('session-state', 'logs', 'ide', 'pkg')
        New-Item -ItemType Directory -Path "$backupPath\copilot" -Force | Out-Null
        Get-ChildItem $copilotDir -Force | Where-Object {
            $_.Name -notin $excludeDirs -and $_.Name -notlike 'session-store*'
        } | ForEach-Object {
            Copy-Item $_.FullName "$backupPath\copilot\$($_.Name)" -Recurse -Force
        }
        Write-Success "Backed up to $backupPath"

        # Enforce retention — keep only the last N backups
        $allBackups = Get-ChildItem $backupRoot -Directory | Sort-Object Name -Descending
        if ($allBackups.Count -gt $maxBackups) {
            $toDelete = $allBackups | Select-Object -Skip $maxBackups
            foreach ($old in $toDelete) {
                Remove-Item $old.FullName -Recurse -Force
                Write-Info "Cleaned up old backup: $($old.Name)"
            }
        }
    }
}

# --- Step 6: Deploy Layer 1 (Base instructions) ---
if ($Mode -eq "consume") {
    Write-Host ""
    Write-Host "  🟦 Layer 1: Base Instructions" -ForegroundColor Cyan

    $templateVars = @{
        USER_NAME = $displayName
        WORKSPACE_PATH = $workspacePath
        GITHUB_PROJECTS_PATH = $githubProjectsPath
        COPILOT_DIR = $copilotDir
        ENVIRONMENTS = "$displayName has $($environments -join ', ') available"
        PERSONA_LIST = ((Get-ChildItem "$repoRoot\personas" -Directory | Where-Object {
            Test-Path "$($_.FullName)\AGENTS.md"
        }).Name | Sort-Object) -join ', '
    }

    $resolvedBase = Resolve-Template -TemplatePath $templateFile -Variables $templateVars

    if ($resolvedBase -match '\{\{') {
        Write-Host "  ⚠️  WARNING: Unresolved variables detected in base template!" -ForegroundColor Red
        $unresolved = [regex]::Matches($resolvedBase, '\{\{(\w+)\}\}') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
        Write-Host "  Missing: $($unresolved -join ', ')" -ForegroundColor Red
    }

    $destBase = "$copilotDir\copilot-instructions.md"
    if ($DryRun) {
        Write-Info "[DRY RUN] Would deploy Layer 1 to $destBase"
    } else {
        New-Item -ItemType Directory -Path $copilotDir -Force | Out-Null
        Set-Content $destBase -Value $resolvedBase -NoNewline
        Write-Success "Layer 1 deployed"
    }
}

# --- Step 7: Deploy Layer 2 (Instance rules) ---
if ($Mode -eq "consume") {
    Write-Host ""
    Write-Host "  🟨 Layer 2: Instance Rules" -ForegroundColor Cyan

    $instanceRulesFile = "$repoRoot\base\instance-rules\$instanceName.instructions.md"
    if (-not (Test-Path $instanceRulesFile)) {
        Write-Host "  ⚠️  No instance rules for '$instanceName' — using personal as default" -ForegroundColor Yellow
        $instanceRulesFile = "$repoRoot\base\instance-rules\personal.instructions.md"
    }

    $activeDir = "$copilotDir\personas\active\.github\instructions"
    if ($DryRun) {
        Write-Info "[DRY RUN] Would deploy Layer 2 from $instanceRulesFile"
    } else {
        New-Item -ItemType Directory -Path $activeDir -Force | Out-Null
        $rulesContent = Resolve-Template -TemplatePath $instanceRulesFile -Variables @{
            WORKSPACE_PATH = $workspacePath
            GITHUB_ACCOUNT = $githubAccount
            DESKTOP_PATH = $knownFolders.desktop
            DOCUMENTS_PATH = $knownFolders.documents
        }
        Set-Content "$activeDir\instance.instructions.md" -Value $rulesContent
        Write-Success "Layer 2 deployed ($instanceName rules)"
    }
}

# --- Step 8: Interactive import of components ---
if ($Mode -eq "consume") {
    $importLog = @()

    foreach ($cat in $categories) {
        $repoDir = "$repoRoot\$($cat.RepoPath)"
        $localDir = if ($cat.LocalPath -eq ".") { $copilotDir } else { "$copilotDir\$($cat.LocalPath)" }

        if (-not (Test-Path $repoDir)) { continue }

        # Gather items
        $items = @()
        if ($cat.Name -eq "Personas") {
            $items = Get-ChildItem $repoDir -Directory | Where-Object { Test-Path "$($_.FullName)\AGENTS.md" } | ForEach-Object {
                @{ Name = $_.Name; RepoFile = "$($_.FullName)\AGENTS.md"; LocalFile = "$localDir\$($_.Name)\AGENTS.md" }
            }
        } elseif ($cat.Name -eq "Skills") {
            $items = Get-ChildItem $repoDir -Directory | Where-Object { Test-Path "$($_.FullName)\SKILL.md" } | ForEach-Object {
                @{ Name = $_.Name; RepoDir = $_.FullName; LocalDir = "$localDir\$($_.Name)"; IsDir = $true }
            }
        } elseif ($cat.Name -eq "Agents") {
            $items = Get-ChildItem $repoDir -Filter "*.agent.md" | ForEach-Object {
                @{ Name = $_.Name; RepoFile = $_.FullName; LocalFile = "$localDir\$($_.Name)" }
            }
            # Also handle agent scripts
            if (Test-Path "$repoDir\scripts") {
                $items += @{ Name = "scripts/"; RepoDir = "$repoDir\scripts"; LocalDir = "$localDir\scripts"; IsDir = $true }
            }
        } elseif ($cat.Name -eq "Scripts") {
            $items = Get-ChildItem $repoDir -Filter "*.ps1" | ForEach-Object {
                @{ Name = $_.Name; RepoFile = $_.FullName; LocalFile = "$localDir\$($_.Name)" }
            }
        }

        if ($items.Count -eq 0) { continue }

        # Calculate statuses
        $new = 0; $differs = 0; $identical = 0
        foreach ($item in $items) {
            if ($item.IsDir) {
                $item.Status = Get-DirStatus -RepoDir $item.RepoDir -LocalDir $item.LocalDir
            } else {
                $item.Status = Get-FileStatus -RepoFile $item.RepoFile -LocalFile $item.LocalFile
            }
            switch ($item.Status) { "new" { $new++ } "differs" { $differs++ } "identical" { $identical++ } }
        }

        $action = Show-CategoryMenu -CategoryName $cat.Name -NewCount $new -DiffersCount $differs -IdenticalCount $identical

        foreach ($item in $items) {
            $itemAction = switch ($action) {
                "import-all" { if ($item.Status -eq "identical") { "skip" } else { "import" } }
                "skip-all" { "skip" }
                "review-each" { Show-ItemMenu -ItemName $item.Name -Status $item.Status }
            }

            # Handle compare — show diff then re-prompt until user picks import or skip
            while ($itemAction -eq "compare") {
                Write-Host ""
                if ($item.IsDir) {
                    # Directory comparison — show files that differ
                    Write-Host "    --- DIRECTORY DIFF: $($item.Name) ---" -ForegroundColor Cyan
                    if (-not (Test-Path $item.LocalDir)) {
                        Write-Host "    (local directory does not exist — all files are new)" -ForegroundColor Green
                    } else {
                        $repoDirN = $item.RepoDir.TrimEnd('\') + '\'
                        $localDirN = $item.LocalDir.TrimEnd('\') + '\'
                        $changedFiles = @()
                        Get-ChildItem $item.RepoDir -Recurse -File | Where-Object { $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc' } | ForEach-Object {
                            $rel = $_.FullName.Substring($repoDirN.Length)
                            $localPath = "$($item.LocalDir)\$rel"
                            if (-not (Test-Path $localPath)) {
                                Write-Host "    + $rel (new in repo)" -ForegroundColor Green
                            } else {
                                $diff = Compare-Object (Get-Content $_.FullName) (Get-Content $localPath)
                                if ($diff.Count -gt 0) {
                                    Write-Host "    ~ $rel (content differs)" -ForegroundColor Yellow
                                    $changedFiles += @{ Rel = $rel; RepoPath = $_.FullName; LocalPath = $localPath }
                                }
                            }
                        }
                        Get-ChildItem $item.LocalDir -Recurse -File | Where-Object { $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc' } | ForEach-Object {
                            $rel = $_.FullName.Substring($localDirN.Length)
                            if (-not (Test-Path "$($item.RepoDir)\$rel")) { Write-Host "    - $rel (only in local)" -ForegroundColor Red }
                        }

                        # Auto-show diff for key files (SKILL.md, AGENTS.md)
                        $keyFiles = $changedFiles | Where-Object { $_.Rel -match '^(SKILL\.md|AGENTS\.md)$' }
                        foreach ($kf in $keyFiles) {
                            Write-Host ""
                            Write-Host "    --- DIFF: $($kf.Rel) ---" -ForegroundColor Cyan
                            $diff = Compare-Object (Get-Content $kf.LocalPath) (Get-Content $kf.RepoPath)
                            $diff | Select-Object -First 30 | ForEach-Object {
                                $indicator = if ($_.SideIndicator -eq '=>') { "+" } else { "-" }
                                $color = if ($_.SideIndicator -eq '=>') { "Green" } else { "Red" }
                                Write-Host "    $indicator $($_.InputObject)" -ForegroundColor $color
                            }
                            if ($diff.Count -gt 30) { Write-Host "    ... ($($diff.Count - 30) more)" -ForegroundColor DarkGray }
                        }
                    }
                } else {
                    # File comparison — show actual diff
                    Write-Host "    --- DIFF: $($item.Name) ---" -ForegroundColor Cyan
                    if (-not (Test-Path $item.LocalFile)) {
                        Write-Host "    (local file does not exist — new from repo)" -ForegroundColor Green
                        Get-Content $item.RepoFile | Select-Object -First 15 | ForEach-Object { Write-Host "    + $_" -ForegroundColor Green }
                    } else {
                        $repoLines = Get-Content $item.RepoFile
                        $localLines = Get-Content $item.LocalFile
                        $diff = Compare-Object $localLines $repoLines -IncludeEqual
                        $diffLines = $diff | Where-Object { $_.SideIndicator -ne '==' }
                        if ($diffLines.Count -eq 0) {
                            Write-Host "    (files are identical)" -ForegroundColor DarkGray
                        } else {
                            $diffLines | Select-Object -First 30 | ForEach-Object {
                                $indicator = if ($_.SideIndicator -eq '=>') { "+" } else { "-" }
                                $color = if ($_.SideIndicator -eq '=>') { "Green" } else { "Red" }
                                Write-Host "    $indicator $($_.InputObject)" -ForegroundColor $color
                            }
                            if ($diffLines.Count -gt 30) { Write-Host "    ... ($($diffLines.Count - 30) more differences)" -ForegroundColor DarkGray }
                        }
                    }
                }
                Write-Host ""
                Write-Host "    [1] Import  [2] Skip"
                $postCompare = Read-Host "    Select (1-2, default: 1)"
                $itemAction = switch ($postCompare) { "2" { "skip" } default { "import" } }
            }

            if ($itemAction -eq "import") {
                if ($DryRun) {
                    Write-Info "[DRY RUN] Would import $($cat.Name)/$($item.Name)"
                } else {
                    if ($item.IsDir) {
                        New-Item -ItemType Directory -Path $item.LocalDir -Force | Out-Null
                        robocopy $item.RepoDir $item.LocalDir /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null
                    } else {
                        $destDir = Split-Path $item.LocalFile -Parent
                        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                        Copy-Item $item.RepoFile $item.LocalFile -Force
                    }
                    Write-Success "$($item.Name) imported"
                }
                $importLog += "$($cat.Name)/$($item.Name) → imported"
            } else {
                if ($item.Status -ne "identical") {
                    Write-Skip "$($item.Name) skipped"
                }
                $importLog += "$($cat.Name)/$($item.Name) → skipped"
            }
        }
    }

    # --- Step 8b: Detect and offer to remove local-only items ---
    Write-Host ""
    Write-Host "  🧹 Checking for local-only items (removed from repo)..." -ForegroundColor Cyan

    $localOnlyItems = @()

    foreach ($cat in $categories) {
        $repoDir = "$repoRoot\$($cat.RepoPath)"
        $localDir = if ($cat.LocalPath -eq ".") { $copilotDir } else { "$copilotDir\$($cat.LocalPath)" }

        if (-not (Test-Path $localDir)) { continue }

        if ($cat.Name -eq "Personas") {
            $repoNames = @(Get-ChildItem $repoDir -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path "$($_.FullName)\AGENTS.md" } | ForEach-Object { $_.Name })
            $localNames = @(Get-ChildItem $localDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'active' -and (Test-Path "$($_.FullName)\AGENTS.md") } | ForEach-Object { $_.Name })
            foreach ($name in $localNames) {
                if ($name -notin $repoNames) {
                    $localOnlyItems += @{ Category = $cat.Name; Name = $name; Path = "$localDir\$name"; IsDir = $true }
                }
            }
        } elseif ($cat.Name -eq "Skills") {
            $repoNames = @(Get-ChildItem $repoDir -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path "$($_.FullName)\SKILL.md" } | ForEach-Object { $_.Name })
            $localNames = @(Get-ChildItem $localDir -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path "$($_.FullName)\SKILL.md" } | ForEach-Object { $_.Name })
            foreach ($name in $localNames) {
                if ($name -notin $repoNames) {
                    $localOnlyItems += @{ Category = $cat.Name; Name = $name; Path = "$localDir\$name"; IsDir = $true }
                }
            }
        } elseif ($cat.Name -eq "Agents") {
            $repoNames = @(Get-ChildItem $repoDir -Filter "*.agent.md" -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
            $localNames = @(Get-ChildItem $localDir -Filter "*.agent.md" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
            foreach ($name in $localNames) {
                if ($name -notin $repoNames) {
                    $localOnlyItems += @{ Category = $cat.Name; Name = $name; Path = "$localDir\$name"; IsDir = $false }
                }
            }
        } elseif ($cat.Name -eq "Scripts") {
            $repoNames = @(Get-ChildItem $repoDir -Filter "*.ps1" -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
            $localNames = @(Get-ChildItem $localDir -Filter "*.ps1" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
            foreach ($name in $localNames) {
                if ($name -notin $repoNames) {
                    $localOnlyItems += @{ Category = $cat.Name; Name = $name; Path = "$localDir\$name"; IsDir = $false }
                }
            }
        }
    }

    if ($localOnlyItems.Count -eq 0) {
        Write-Info "No local-only items found — local matches repo"
    } else {
        Write-Host "  Found $($localOnlyItems.Count) local-only item(s) not in repo:" -ForegroundColor Yellow
        foreach ($item in $localOnlyItems) {
            Write-Host "    📁 $($item.Category)/$($item.Name)" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "  [1] Delete All — remove local-only items to match repo"
        Write-Host "  [2] Skip All — keep local copies"
        Write-Host "  [3] Review Each — decide per item"
        Write-Host ""
        $cleanupChoice = Read-Host "  Select (1-3, default: 2)"

        foreach ($item in $localOnlyItems) {
            $deleteIt = switch ($cleanupChoice) {
                "1" { $true }
                "3" {
                    Write-Host "    $($item.Category)/$($item.Name) — local only (not in repo)" -ForegroundColor Yellow
                    Write-Host "    [1] Delete  [2] Keep"
                    $perItem = Read-Host "    Select (1-2, default: 2)"
                    $perItem -eq "1"
                }
                default { $false }
            }

            if ($deleteIt) {
                if ($DryRun) {
                    Write-Info "[DRY RUN] Would delete $($item.Path)"
                } else {
                    if ($item.IsDir) {
                        Remove-Item $item.Path -Recurse -Force
                    } else {
                        Remove-Item $item.Path -Force
                    }
                    Write-Success "$($item.Category)/$($item.Name) deleted"
                }
                $importLog += "$($item.Category)/$($item.Name) → deleted (local-only)"
            } else {
                Write-Skip "$($item.Category)/$($item.Name) kept"
                $importLog += "$($item.Category)/$($item.Name) → kept (local-only)"
            }
        }
    }
}

# --- Step 9: Deploy MCP config ---
if ($Mode -eq "consume") {
    Write-Host ""
    Write-Host "  📡 MCP Server Configuration" -ForegroundColor Cyan

    # CLI MCP
    if ($clients -contains "cli") {
        $mcpSource = "$repoRoot\mcp\mcp-config.$mcpProfile.json"
        if (-not (Test-Path $mcpSource)) { $mcpSource = "$repoRoot\mcp\mcp-config.universal.json" }
        if (Test-Path $mcpSource) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Would deploy CLI MCP config"
            } else {
                Copy-Item $mcpSource "$copilotDir\mcp-config.json" -Force
                Write-Success "CLI MCP config deployed ($mcpProfile)"
            }
        }
    }

    # VS Code MCP
    if ($clients -contains "vscode" -or $clients -contains "vscode-insiders") {
        $vscodeMcpSource = "$repoRoot\mcp\mcp.vscode.universal.json"
        if (Test-Path $vscodeMcpSource) {
            $targets = @()
            if ($clients -contains "vscode") { $targets += "$env:APPDATA\Code\User\mcp.json" }
            if ($clients -contains "vscode-insiders") { $targets += "$env:APPDATA\Code - Insiders\User\mcp.json" }
            foreach ($t in $targets) {
                if ($DryRun) {
                    Write-Info "[DRY RUN] Would deploy VS Code MCP to $t"
                } else {
                    Copy-Item $vscodeMcpSource $t -Force
                    Write-Success "VS Code MCP deployed to $t"
                }
            }
        }
    }
}

# --- Step 10: Set up VS Code skill/agent discovery ---
if ($Mode -eq "consume" -and ($clients -contains "vscode" -or $clients -contains "vscode-insiders")) {
    Write-Host ""
    Write-Host "  🔧 VS Code Configuration" -ForegroundColor Cyan

    $vsTargets = @()
    if ($clients -contains "vscode") { $vsTargets += "$env:APPDATA\Code\User\settings.json" }
    if ($clients -contains "vscode-insiders") { $vsTargets += "$env:APPDATA\Code - Insiders\User\settings.json" }

    foreach ($settingsPath in $vsTargets) {
        if (Test-Path $settingsPath) {
            $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json

            # Ensure agentSkillsLocations includes ~/.copilot/skills
            $skillsLocSetting = 'chat.agentSkillsLocations'
            $skillsDir = "$copilotDir\skills"
            $currentLocs = $settings.PSObject.Properties[$skillsLocSetting]

            if (-not $currentLocs -or -not ($currentLocs.Value.PSObject.Properties[$skillsDir])) {
                if ($DryRun) {
                    Write-Info "[DRY RUN] Would add $skillsDir to $skillsLocSetting"
                } else {
                    if (-not $currentLocs) {
                        $settings | Add-Member -NotePropertyName $skillsLocSetting -NotePropertyValue @{ $skillsDir = $true } -Force
                    } else {
                        $currentLocs.Value | Add-Member -NotePropertyName $skillsDir -NotePropertyValue $true -Force
                    }
                    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath
                    Write-Success "Added skills location to VS Code settings"
                }
            } else {
                Write-Info "Skills location already configured in VS Code"
            }
        }
    }
}

# --- Step 11: Set environment variable ---
if ($Mode -eq "consume") {
    Write-Host ""
    Write-Host "  🔑 Environment Variable" -ForegroundColor Cyan

    $envVar = "COPILOT_CUSTOM_INSTRUCTIONS_DIRS"
    $envVal = "$copilotDir\personas\active"
    $currentVal = [System.Environment]::GetEnvironmentVariable($envVar, "User")

    if ($currentVal -ne $envVal) {
        if ($DryRun) {
            Write-Info "[DRY RUN] Would set $envVar = $envVal"
        } else {
            [System.Environment]::SetEnvironmentVariable($envVar, $envVal, "User")
            Write-Success "$envVar set"
        }
    } else {
        Write-Info "$envVar already set correctly"
    }
}

# --- Step 12: Set active persona ---
if ($Mode -eq "consume") {
    Write-Host ""
    Write-Host "  🎭 Default Persona" -ForegroundColor Cyan
    $activeFile = "$copilotDir\personas\active\AGENTS.md"

    if (-not (Test-Path $activeFile)) {
        $defaultPersona = "productivity"
        $defaultSource = "$copilotDir\personas\$defaultPersona\AGENTS.md"
        if (Test-Path $defaultSource) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Would set default persona to $defaultPersona"
            } else {
                Copy-Item $defaultSource $activeFile -Force
                Write-Success "Default persona set to $defaultPersona"
            }
        }
    } else {
        Write-Info "Active persona already set"
    }
}

# --- Summary ---
Write-Banner "Setup Complete"

Write-Host "  Instance:    $instanceName" -ForegroundColor DarkGray
Write-Host "  Display:     $displayName" -ForegroundColor DarkGray
Write-Host "  Workspace:   $workspacePath" -ForegroundColor DarkGray
Write-Host "  GitHub:      $githubAccount" -ForegroundColor DarkGray
Write-Host "  Clients:     $($clients -join ', ')" -ForegroundColor DarkGray
Write-Host "  MCP Profile: $mcpProfile" -ForegroundColor DarkGray

if ($Mode -eq "consume" -and $importLog) {
    Write-Host ""
    Write-Host "  Import Summary:" -ForegroundColor Cyan
    $imported = ($importLog | Where-Object { $_ -match 'imported' }).Count
    $skipped = ($importLog | Where-Object { $_ -match 'skipped' }).Count
    Write-Host "    $imported imported, $skipped skipped"
}

if ($backupPath -and (Test-Path $backupPath)) {
    Write-Host ""
    Write-Host "  💾 Backup at: $backupPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "  • Open a new terminal and launch 'copilot'"
Write-Host "  • Run /instructions to verify all 3 layers loaded"
Write-Host "  • Run Switch-CopilotPersona.ps1 -List to see available personas"
Write-Host ""

<#
.SYNOPSIS
    Squad CLI setup and maintenance script for Copilot CLI integration.

.DESCRIPTION
    Idempotent bootstrap script that installs Squad CLI globally, initializes
    Squad in the current git repo, updates Squad artifacts, or reports status.
    Designed to be invoked by the squad-setup Copilot CLI agent.

.PARAMETER Action
    The action to perform: install-cli, init, update, status, or auto.
    - install-cli: Install/update Squad CLI globally via npm.
    - init: Initialize Squad in the current git repo (idempotent).
    - update: Update Squad artifacts to latest version.
    - status: Report current Squad state without changing anything.
    - auto: (Default) Detect state and do the right thing automatically.

.PARAMETER Force
    Skip confirmation prompts and overwrite files (creates .bak backups).

.PARAMETER NoBackup
    When used with -Force, skip creating .bak backup files before overwriting.

.EXAMPLE
    .\setup-squad.ps1
    .\setup-squad.ps1 -Action init
    .\setup-squad.ps1 -Action update
    .\setup-squad.ps1 -Action status
    .\setup-squad.ps1 -Action install-cli
#>

[CmdletBinding()]
param(
    [ValidateSet('install-cli', 'init', 'update', 'status', 'auto')]
    [string]$Action = 'auto',

    [switch]$Force,
    [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Step  { param([string]$Msg) Write-Host "  ▸ $Msg" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Msg) Write-Host "  ✓ $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "  ⚠ $Msg" -ForegroundColor Yellow }
function Write-Err   { param([string]$Msg) Write-Host "  ✗ $Msg" -ForegroundColor Red }
function Write-Info  { param([string]$Msg) Write-Host "  ℹ $Msg" -ForegroundColor Gray }

function Test-InGitRepo {
    try {
        $null = git rev-parse --is-inside-work-tree 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-SquadInitialized {
    return (Test-Path -Path '.squad' -PathType Container) -and (Test-Path -Path '.squad\team.md')
}

function Get-SquadCliVersion {
    try {
        $ver = & squad --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            # squad --version might output something like "squad-cli/0.8.25" or just "0.8.25"
            $ver = $ver -replace '^.*?(\d+\.\d+\.\d+.*)$', '$1'
            return $ver.Trim()
        }
    } catch {}
    return $null
}

function Get-LatestNpmVersion {
    param([string]$Package = '@bradygaster/squad-cli')
    try {
        $ver = & npm view $Package version 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return $ver.Trim()
        }
    } catch {}
    return $null
}

function Get-SquadManagedFiles {
    # Returns list of files that squad init/upgrade creates/manages
    if (-not (Test-Path '.squad')) { return @() }
    return Get-ChildItem -Path '.squad' -Recurse -File | ForEach-Object { $_.FullName }
}

function Backup-FileIfEdited {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath)) { return $false }
    if ($NoBackup) { return $false }

    $bakPath = "$FilePath.bak"
    Copy-Item -Path $FilePath -Destination $bakPath -Force
    Write-Info "Backed up: $FilePath → $bakPath"
    return $true
}

# ── Actions ──────────────────────────────────────────────────────────────────

function Invoke-InstallCli {
    Write-Host "`n🔧 Squad CLI — Install/Update" -ForegroundColor Magenta

    # Check Node.js
    $nodeVer = node --version 2>$null
    if (-not $nodeVer) {
        Write-Err "Node.js is not installed. Squad requires Node.js >= 20.0.0."
        Write-Info "Install from https://nodejs.org or via nvm-windows."
        return $false
    }
    $nodeMajor = [int]($nodeVer -replace '^v(\d+)\..*', '$1')
    if ($nodeMajor -lt 20) {
        Write-Err "Node.js $nodeVer is too old. Squad requires >= 20.0.0."
        return $false
    }
    Write-Ok "Node.js $nodeVer"

    # Check current install
    $currentVer = Get-SquadCliVersion
    $latestVer = Get-LatestNpmVersion

    if ($currentVer) {
        Write-Info "Currently installed: squad-cli $currentVer"
        if ($latestVer -and $currentVer -eq $latestVer) {
            Write-Ok "Already at latest version ($latestVer). Nothing to do."
            return $true
        }
        if ($latestVer) {
            Write-Step "Updating squad-cli $currentVer → $latestVer"
        } else {
            Write-Step "Reinstalling squad-cli (could not check latest version)"
        }
    } else {
        Write-Step "Installing @bradygaster/squad-cli globally..."
    }

    npm install -g @bradygaster/squad-cli 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "npm install failed. Check npm permissions or network."
        return $false
    }

    $newVer = Get-SquadCliVersion
    if ($newVer) {
        Write-Ok "Squad CLI $newVer installed globally."
    } else {
        Write-Warn "Install completed but 'squad' command not found. You may need to restart your shell."
    }
    return $true
}

function Invoke-Init {
    Write-Host "`n🚀 Squad — Initialize" -ForegroundColor Magenta

    if (-not (Test-InGitRepo)) {
        Write-Err "Not inside a git repository. Squad requires a git repo."
        Write-Info "Run 'git init' first, then retry."
        return $false
    }
    Write-Ok "Git repo detected: $(git rev-parse --show-toplevel)"

    # Ensure Squad CLI is available
    if (-not (Get-SquadCliVersion)) {
        Write-Step "Squad CLI not found. Installing first..."
        $installed = Invoke-InstallCli
        if (-not $installed) { return $false }
    }

    # Check if already initialized
    if (Test-SquadInitialized) {
        Write-Ok "Squad is already initialized in this repo."
        Write-Info "Use '-Action update' to refresh Squad artifacts."
        return $true
    }

    # Run squad init
    Write-Step "Running 'squad init'..."
    squad init 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "squad init failed (exit code $LASTEXITCODE)."
        return $false
    }

    if (Test-SquadInitialized) {
        Write-Ok "Squad initialized successfully!"
        Write-Host "`n  📁 Created files:" -ForegroundColor White
        Get-ChildItem -Path '.squad' -Recurse -File | ForEach-Object {
            Write-Info "  .squad\$($_.FullName.Substring((Resolve-Path '.squad').Path.Length + 1))"
        }
        Write-Host ""
        Write-Info "Next: commit the .squad/ folder, then open Copilot and select the Squad agent."
    } else {
        Write-Warn "squad init ran but .squad/team.md was not created. Check output above."
    }
    return $true
}

function Invoke-Update {
    Write-Host "`n🔄 Squad — Update" -ForegroundColor Magenta

    if (-not (Test-InGitRepo)) {
        Write-Err "Not inside a git repository."
        return $false
    }

    if (-not (Test-SquadInitialized)) {
        Write-Warn "Squad is not initialized in this repo. Running init instead..."
        return Invoke-Init
    }

    # Ensure Squad CLI is up to date
    $currentVer = Get-SquadCliVersion
    $latestVer = Get-LatestNpmVersion
    if ($currentVer -and $latestVer -and $currentVer -ne $latestVer) {
        Write-Step "Squad CLI update available: $currentVer → $latestVer"
        Write-Step "Updating CLI first..."
        Invoke-InstallCli | Out-Null
    } elseif ($currentVer) {
        Write-Ok "Squad CLI is at latest ($currentVer)"
    }

    # Snapshot current files for diff
    $beforeFiles = @{}
    Get-SquadManagedFiles | ForEach-Object {
        $beforeFiles[$_] = (Get-FileHash -Path $_ -Algorithm SHA256).Hash
    }

    # Back up files that might have local edits
    if (-not $Force) {
        $editedFiles = @()
        foreach ($file in $beforeFiles.Keys) {
            # Check if file has uncommitted changes
            $relPath = Resolve-Path -Relative $file 2>$null
            if (-not $relPath) { $relPath = $file }
            $gitStatus = git status --porcelain -- $relPath 2>$null
            if ($gitStatus) {
                $editedFiles += $relPath
            }
        }
        if ($editedFiles.Count -gt 0) {
            Write-Warn "These Squad files have uncommitted local edits:"
            $editedFiles | ForEach-Object { Write-Info "  $_" }
            Write-Step "Creating .bak backups before upgrade..."
            $editedFiles | ForEach-Object { Backup-FileIfEdited $_ }
        }
    } elseif (-not $NoBackup) {
        # Force mode: back up everything
        $beforeFiles.Keys | ForEach-Object { Backup-FileIfEdited $_ }
    }

    # Run squad upgrade
    Write-Step "Running 'squad upgrade'..."
    squad upgrade 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "squad upgrade failed (exit code $LASTEXITCODE)."
        return $false
    }

    # Diff report
    $afterFiles = @{}
    Get-SquadManagedFiles | ForEach-Object {
        $afterFiles[$_] = (Get-FileHash -Path $_ -Algorithm SHA256).Hash
    }

    $created = @()
    $modified = @()
    $unchanged = @()

    foreach ($file in $afterFiles.Keys) {
        if (-not $beforeFiles.ContainsKey($file)) {
            $created += $file
        } elseif ($beforeFiles[$file] -ne $afterFiles[$file]) {
            $modified += $file
        } else {
            $unchanged += $file
        }
    }

    Write-Host "`n  📋 Update Summary:" -ForegroundColor White
    if ($created.Count -gt 0) {
        Write-Host "  Created ($($created.Count)):" -ForegroundColor Green
        $created | ForEach-Object { Write-Info "    + $_" }
    }
    if ($modified.Count -gt 0) {
        Write-Host "  Modified ($($modified.Count)):" -ForegroundColor Yellow
        $modified | ForEach-Object { Write-Info "    ~ $_" }
    }
    if ($created.Count -eq 0 -and $modified.Count -eq 0) {
        Write-Ok "All files already up to date. No changes made."
    }

    return $true
}

function Invoke-Status {
    Write-Host "`n📊 Squad — Status" -ForegroundColor Magenta

    # Git repo check
    if (Test-InGitRepo) {
        Write-Ok "Git repo: $(git rev-parse --show-toplevel)"
    } else {
        Write-Warn "Not in a git repo."
    }

    # Squad CLI
    $cliVer = Get-SquadCliVersion
    if ($cliVer) {
        Write-Ok "Squad CLI: $cliVer (global)"
        $latestVer = Get-LatestNpmVersion
        if ($latestVer -and $cliVer -ne $latestVer) {
            Write-Warn "Update available: $cliVer → $latestVer"
        } elseif ($latestVer) {
            Write-Ok "CLI is at latest version"
        }
    } else {
        Write-Warn "Squad CLI: not installed"
    }

    # Squad init state
    if (Test-SquadInitialized) {
        Write-Ok "Squad initialized in this repo"
        $fileCount = (Get-SquadManagedFiles).Count
        Write-Info "$fileCount files in .squad/"

        # Check for uncommitted changes in .squad/
        $dirtyFiles = git status --porcelain -- '.squad/' 2>$null
        if ($dirtyFiles) {
            Write-Warn "Uncommitted changes in .squad/:"
            $dirtyFiles | ForEach-Object { Write-Info "  $_" }
        } else {
            Write-Ok "All .squad/ files are committed"
        }
    } else {
        Write-Info "Squad not initialized in this repo"
    }

    # Node.js
    $nodeVer = node --version 2>$null
    if ($nodeVer) {
        Write-Ok "Node.js: $nodeVer"
    } else {
        Write-Err "Node.js: not found"
    }

    # gh CLI (needed for issues/PRs)
    $ghVer = gh --version 2>$null | Select-Object -First 1
    if ($ghVer) {
        Write-Ok "GitHub CLI: $ghVer"
    } else {
        Write-Info "GitHub CLI: not installed (optional, needed for issues/PR triage)"
    }
}

function Invoke-Auto {
    Write-Host "`n🤖 Squad — Auto-Detect" -ForegroundColor Magenta

    # Step 1: Ensure CLI is installed
    $cliVer = Get-SquadCliVersion
    if (-not $cliVer) {
        Write-Step "Squad CLI not installed. Installing..."
        $installed = Invoke-InstallCli
        if (-not $installed) {
            Write-Err "Cannot proceed without Squad CLI."
            return $false
        }
    } else {
        # Check for CLI update
        $latestVer = Get-LatestNpmVersion
        if ($latestVer -and $cliVer -ne $latestVer) {
            Write-Step "Squad CLI update available: $cliVer → $latestVer. Updating..."
            Invoke-InstallCli | Out-Null
        } else {
            Write-Ok "Squad CLI $cliVer (latest)"
        }
    }

    # Step 2: Check git repo
    if (-not (Test-InGitRepo)) {
        Write-Err "Not inside a git repository. cd into a repo and retry."
        return $false
    }

    # Step 3: Init or update
    if (-not (Test-SquadInitialized)) {
        Write-Step "Squad not initialized. Running init..."
        return Invoke-Init
    } else {
        Write-Ok "Squad already initialized."
        Write-Step "Checking for updates..."
        return Invoke-Update
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────

Write-Host "╔══════════════════════════════════════╗" -ForegroundColor DarkCyan
Write-Host "║  Squad Setup — Copilot CLI Agent     ║" -ForegroundColor DarkCyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor DarkCyan

switch ($Action) {
    'install-cli' { Invoke-InstallCli }
    'init'        { Invoke-Init }
    'update'      { Invoke-Update }
    'status'      { Invoke-Status }
    'auto'        { Invoke-Auto }
}

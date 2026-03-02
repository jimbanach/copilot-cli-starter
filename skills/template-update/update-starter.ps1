<#
.SYNOPSIS
    Fetch, merge, and deploy upstream starter updates in one step.

.DESCRIPTION
    Fetches from upstream, merges changes, and deploys updated files
    directly to ~/.copilot/. Handles new files, modified files, AND
    deleted files.

.PARAMETER DryRun
    Show what would change without merging or deploying.
#>

param([switch]$DryRun)

$copilotDir = "$env:USERPROFILE\.copilot"

# Find the copilot-cli-starter repo
$repoRoot = $null
if ((Get-Item .).Name -eq 'copilot-cli-starter' -and (Test-Path '.git')) {
    $repoRoot = (Get-Location).Path
} else {
    foreach ($path in @("$env:USERPROFILE\copilot-cli-starter", "$env:USERPROFILE\CopilotWorkspace\copilot-cli-starter")) {
        if (Test-Path "$path\.git") {
            $repoRoot = $path
            break
        }
    }
}

if (-not $repoRoot) {
    Write-Host "Error: Could not find copilot-cli-starter repo" -ForegroundColor Red
    exit 1
}

Write-Host "Repo: $repoRoot" -ForegroundColor DarkGray

# Verify upstream remote
$upstream = git -C $repoRoot remote get-url upstream 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Adding upstream remote..." -ForegroundColor Cyan
    git -C $repoRoot remote add upstream "https://github.com/jimbanach/copilot-cli-starter.git"
}

# Fetch
Write-Host "Fetching upstream..." -ForegroundColor Cyan
git -C $repoRoot fetch upstream 2>&1 | Out-Null

# Check for new commits
$newCommits = git -C $repoRoot --no-pager log HEAD..upstream/main --oneline 2>&1
if (-not $newCommits -or "$newCommits".Trim() -eq "") {
    Write-Host "`nAlready up to date - no new upstream commits." -ForegroundColor Green
    exit 0
}

# Show what's new — use --diff-filter to categorize changes
$changedFiles = @(git -C $repoRoot --no-pager diff HEAD..upstream/main --name-status 2>&1)
Write-Host "`nUpstream has updates:" -ForegroundColor Cyan
$newCommits | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
Write-Host "`nChanged files:" -ForegroundColor Cyan
foreach ($f in $changedFiles) { 
    $parts = $f -split '\t'
    $status = $parts[0]
    $name = $parts[1]
    $icon = switch ($status) { "A" { "+" } "M" { "~" } "D" { "-" } default { "?" } }
    Write-Host "  $icon $name" -ForegroundColor $(switch ($status) { "A" { "Green" } "D" { "Red" } default { "Yellow" } })
}

if ($DryRun) {
    Write-Host "`n[DRY RUN] Would merge and deploy $($changedFiles.Count) files." -ForegroundColor DarkGray
    exit 0
}

# Merge
Write-Host "`nMerging..." -ForegroundColor Cyan
$mergeResult = git -C $repoRoot merge upstream/main 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Merge conflict! Resolve manually, then re-run." -ForegroundColor Red
    Write-Host $mergeResult
    exit 1
}

# Deploy changed files
Write-Host "`nDeploying to ~/.copilot/..." -ForegroundColor Cyan
$deployed = 0
$deleted = 0
$skipped = 0

foreach ($entry in $changedFiles) {
    $parts = $entry -split '\t'
    $status = $parts[0]
    $file = $parts[1]

    # Determine destination
    $dest = $null
    if ($file -match '^personas/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^skills/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^agents/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^scripts/(.+)') { $dest = Join-Path $copilotDir $matches[1] }

    if (-not $dest) {
        Write-Host "  SKIP: $file (base/instance - run init.ps1)" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    if ($status -eq "D") {
        # File was deleted upstream — remove locally too
        if (Test-Path $dest) {
            Remove-Item $dest -Force
            Write-Host "  DEL: $file" -ForegroundColor Red
            $deleted++
        }
    } else {
        # File was added or modified — copy it
        $src = Join-Path $repoRoot $file
        if (Test-Path $src) {
            $destDir = Split-Path $dest -Parent
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory $destDir -Force | Out-Null }
            Copy-Item $src $dest -Force
            Write-Host "  OK: $file" -ForegroundColor Green
            $deployed++
        }
    }
}

Write-Host "`nDeployment Summary:" -ForegroundColor Cyan
Write-Host "  Deployed: $deployed files" -ForegroundColor Green
if ($deleted -gt 0) { Write-Host "  Deleted:  $deleted files" -ForegroundColor Red }
if ($skipped -gt 0) { Write-Host "  Skipped:  $skipped files (run init.ps1)" -ForegroundColor Yellow }

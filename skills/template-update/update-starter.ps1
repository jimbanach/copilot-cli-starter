<#
.SYNOPSIS
    Fetch, merge, and deploy upstream starter updates in one step.

.DESCRIPTION
    Fetches from upstream, merges changes, and deploys updated files
    directly to ~/.copilot/. This is the script the template-update
    skill should invoke instead of running git commands separately.

.PARAMETER DryRun
    Show what would change without merging or deploying.
#>

param([switch]$DryRun)

$repoRoot = $PSScriptRoot | Split-Path  # script is in skills/template-update/
$copilotDir = "$env:USERPROFILE\.copilot"

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
if (-not $newCommits -or $newCommits -match "^$") {
    Write-Host "`n✅ Already up to date — no new upstream commits." -ForegroundColor Green
    exit 0
}

# Show what's new
$changedFiles = @(git -C $repoRoot --no-pager diff HEAD..upstream/main --name-only 2>&1)
Write-Host "`n📊 Upstream has updates:" -ForegroundColor Cyan
Write-Host ($newCommits | ForEach-Object { "  $_" }) -ForegroundColor White
Write-Host "`nChanged files:" -ForegroundColor Cyan
foreach ($f in $changedFiles) { Write-Host "  $f" -ForegroundColor Yellow }

if ($DryRun) {
    Write-Host "`n[DRY RUN] Would merge and deploy $($changedFiles.Count) files." -ForegroundColor DarkGray
    exit 0
}

# Merge
Write-Host "`nMerging..." -ForegroundColor Cyan
$mergeResult = git -C $repoRoot merge upstream/main 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Merge conflict! Resolve manually, then re-run." -ForegroundColor Red
    Write-Host $mergeResult
    exit 1
}

# Deploy changed files to ~/.copilot/
Write-Host "`nDeploying to ~/.copilot/..." -ForegroundColor Cyan
$deployed = 0
$skipped = 0

foreach ($file in $changedFiles) {
    $dest = $null
    $src = Join-Path $repoRoot $file

    if (-not (Test-Path $src)) { continue }  # file was deleted upstream

    if ($file -match '^personas/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^skills/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^agents/') { $dest = Join-Path $copilotDir $file }
    elseif ($file -match '^scripts/(.+)') { $dest = Join-Path $copilotDir $matches[1] }

    if ($dest) {
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory $destDir -Force | Out-Null }
        Copy-Item $src $dest -Force
        Write-Host "  ✅ $file" -ForegroundColor Green
        $deployed++
    } else {
        Write-Host "  ⏭️  $file (requires init.ps1)" -ForegroundColor DarkGray
        $skipped++
    }
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ Deployed: $deployed files to ~/.copilot/" -ForegroundColor Green
if ($skipped -gt 0) {
    Write-Host "⏭️  Skipped: $skipped files (base/instance — run init.ps1 to apply)" -ForegroundColor Yellow
}

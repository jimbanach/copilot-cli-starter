# Playwright session lock manager
# Usage:
#   playwright-lock.ps1 check    — returns 0 if available, 1 if locked (shows who has it)
#   playwright-lock.ps1 acquire  — acquires lock, returns 0 on success, 1 if already locked
#   playwright-lock.ps1 release  — releases lock
#   playwright-lock.ps1 status   — human-readable status

param(
    [Parameter(Position=0)]
    [ValidateSet("check","acquire","release","status")]
    [string]$Action = "status"
)

$LockFile = "$env:USERPROFILE\.copilot\.playwright-lock"

function Get-LockInfo {
    if (-not (Test-Path $LockFile)) { return $null }
    $content = Get-Content $LockFile -Raw | ConvertFrom-Json
    # Verify the owning process is still alive
    $proc = Get-Process -Id $content.pid -ErrorAction SilentlyContinue
    if (-not $proc) {
        # Stale lock — owner process died without releasing
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        return $null
    }
    return $content
}

switch ($Action) {
    "check" {
        $lock = Get-LockInfo
        if ($lock) {
            Write-Host "LOCKED by PID $($lock.pid) (session: $($lock.session)) since $($lock.acquired)"
            exit 1
        } else {
            Write-Host "AVAILABLE"
            exit 0
        }
    }
    "acquire" {
        $lock = Get-LockInfo
        if ($lock) {
            Write-Error "Playwright is already in use by PID $($lock.pid) (session: $($lock.session)) since $($lock.acquired). Wait for that session to finish or run: playwright-lock.ps1 release"
            exit 1
        }
        $info = @{
            pid = $PID
            session = if ($env:COPILOT_SESSION_ID) { $env:COPILOT_SESSION_ID } else { "unknown" }
            acquired = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            host = $env:COMPUTERNAME
        } | ConvertTo-Json
        $info | Set-Content $LockFile -Force
        Write-Host "Lock acquired (PID: $PID)"
        exit 0
    }
    "release" {
        if (Test-Path $LockFile) {
            Remove-Item $LockFile -Force
            Write-Host "Lock released"
        } else {
            Write-Host "No lock to release"
        }
        exit 0
    }
    "status" {
        $lock = Get-LockInfo
        if ($lock) {
            Write-Host "Playwright is LOCKED"
            Write-Host "  Owner PID:  $($lock.pid)"
            Write-Host "  Session:    $($lock.session)"
            Write-Host "  Since:      $($lock.acquired)"
            Write-Host ""
            Write-Host "To force release: pwsh $PSCommandPath release"
        } else {
            Write-Host "Playwright is AVAILABLE"
        }
    }
}

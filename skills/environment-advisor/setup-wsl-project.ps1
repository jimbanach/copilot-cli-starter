<#
.SYNOPSIS
    Bootstrap a project in WSL Ubuntu.

.DESCRIPTION
    Creates a project directory in WSL, optionally initializes git,
    and sets up basic project structure mirroring the CopilotWorkspace layout.

.PARAMETER ProjectName
    Name of the project to create.

.PARAMETER ProjectPath
    Optional. Custom path in WSL. Defaults to ~/projects/<ProjectName>.

.EXAMPLE
    .\setup-wsl-project.ps1 -ProjectName "security-tool-eval"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectName,

    [string]$ProjectPath
)

if (-not $ProjectPath) {
    $ProjectPath = "~/projects/$ProjectName"
}

Write-Host ""
Write-Host "  Setting up WSL project: $ProjectName" -ForegroundColor Cyan
Write-Host "  Path: $ProjectPath" -ForegroundColor DarkGray
Write-Host ""

# Create project directory structure in WSL
$commands = @(
    "mkdir -p $ProjectPath/.github"
    "mkdir -p $ProjectPath/src"
    "echo '# $ProjectName' > $ProjectPath/README.md"
    "cat > $ProjectPath/.github/copilot-instructions.md << 'EOF'`n# Project: $ProjectName`n`n## Environment`nThis project runs in WSL (Ubuntu) for isolation.`n`n## Context`n[Add project-specific instructions here]`nEOF"
    "cat > $ProjectPath/project.json << 'EOF'`n{`n  `"name`": `"$ProjectName`",`n  `"environment`": `"wsl`",`n  `"environment_reason`": `"Project requires Linux isolation`",`n  `"created`": `"$(Get-Date -Format 'yyyy-MM-dd')`",`n  `"status`": `"active`"`n}`nEOF"
    "cd $ProjectPath && git init"
)

foreach ($cmd in $commands) {
    wsl -d Ubuntu -- bash -c $cmd
}

Write-Host ""
Write-Host "  WSL project created at $ProjectPath" -ForegroundColor Green
Write-Host "  To access: wsl -d Ubuntu --cd $ProjectPath" -ForegroundColor Yellow
Write-Host ""

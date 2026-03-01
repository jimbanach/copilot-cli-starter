<#
.SYNOPSIS
    Switch between Copilot CLI personas (3-layer model).

.DESCRIPTION
    Copies the selected persona's AGENTS.md to ~/.copilot/personas/active/AGENTS.md
    (Layer 3). Layers 1 (base) and 2 (instance rules) are never touched.
    Auto-detects new personas and updates the base instructions persona list.

.PARAMETER Persona
    Name of the persona to switch to. If not provided, shows interactive menu.

.PARAMETER Target
    Deployment target: cli, vscode, all, or auto (default). Auto detects which clients are installed.

.PARAMETER List
    List all available personas with descriptions without switching.

.EXAMPLE
    .\Switch-CopilotPersona.ps1
    # Interactive menu to select a persona

.EXAMPLE
    .\Switch-CopilotPersona.ps1 -Persona productivity
    # Directly switch to the productivity persona

.EXAMPLE
    .\Switch-CopilotPersona.ps1 -List
    # Show all personas with descriptions
#>

param(
    [string]$Persona,
    [ValidateSet("cli", "vscode", "all", "auto")]
    [string]$Target = "auto",
    [switch]$List
)

$personaRoot = "$HOME\.copilot\personas"
$activeDir = "$HOME\.copilot\personas\active"
$activeFile = "$activeDir\AGENTS.md"
$baseFile = "$HOME\.copilot\copilot-instructions.md"

# Helper: extract persona description from first line after "# Persona:"
function Get-PersonaDescription {
    param([string]$PersonaName)
    # Try AGENTS.md first, fall back to copilot-instructions.md
    $file = Join-Path $personaRoot "$PersonaName\AGENTS.md"
    if (-not (Test-Path $file)) {
        $file = Join-Path $personaRoot "$PersonaName\copilot-instructions.md"
    }
    if (Test-Path $file) {
        $firstLine = (Get-Content $file -TotalCount 1) -replace "^# Persona:\s*", ""
        return $firstLine
    }
    return "(no description)"
}

# Get available personas (dirs with AGENTS.md or copilot-instructions.md, excluding 'active')
$personas = Get-ChildItem -Path $personaRoot -Directory | Where-Object { $_.Name -ne 'active' } | Where-Object {
    (Test-Path "$($_.FullName)\AGENTS.md") -or (Test-Path "$($_.FullName)\copilot-instructions.md")
} | Select-Object -ExpandProperty Name

if ($personas.Count -eq 0) {
    Write-Host "No personas found in $personaRoot" -ForegroundColor Red
    exit 1
}

# Auto-detect new personas and update base instructions
if (Test-Path $baseFile) {
    $baseContent = Get-Content $baseFile -Raw
    $personaListMatch = [regex]::Match($baseContent, "Available personas:\s*(.+)")
    if ($personaListMatch.Success) {
        $listedPersonas = $personaListMatch.Groups[1].Value -split ',\s*' | ForEach-Object { $_.Trim().TrimEnd('.') }
        $newPersonas = $personas | Where-Object { $_ -notin $listedPersonas }
        if ($newPersonas.Count -gt 0) {
            $updatedList = ($personas | Sort-Object) -join ', '
            $baseContent = $baseContent -replace "Available personas:\s*.+", "Available personas: $updatedList."
            Set-Content -Path $baseFile -Value $baseContent -NoNewline
            Write-Host "  📝 Updated base instructions with new persona(s): $($newPersonas -join ', ')" -ForegroundColor Cyan
        }
    }
}

# Check current persona by comparing active AGENTS.md
$currentPersona = $null
if (Test-Path $activeFile) {
    $activeContent = Get-Content $activeFile -Raw -ErrorAction SilentlyContinue
    foreach ($p in $personas) {
        $pFile = "$personaRoot\$p\AGENTS.md"
        if (-not (Test-Path $pFile)) { $pFile = "$personaRoot\$p\copilot-instructions.md" }
        $pContent = Get-Content $pFile -Raw -ErrorAction SilentlyContinue
        if ($activeContent -eq $pContent) {
            $currentPersona = $p
            break
        }
    }
}

# List mode
if ($List) {
    Write-Host ""
    Write-Host "  Available Copilot Personas" -ForegroundColor Cyan
    Write-Host "  --------------------------" -ForegroundColor Cyan
    Write-Host ""
    foreach ($p in $personas) {
        $desc = Get-PersonaDescription $p
        $marker = if ($p -eq $currentPersona) { " (active)" } else { "" }
        $color = if ($p -eq $currentPersona) { "Green" } else { "White" }
        Write-Host "  • $p$marker" -ForegroundColor $color
        Write-Host "    $desc" -ForegroundColor DarkGray
    }
    Write-Host ""
    exit 0
}

# If no persona specified, show interactive menu
if (-not $Persona) {
    Write-Host ""
    Write-Host "  Available Copilot Personas" -ForegroundColor Cyan
    Write-Host "  --------------------------" -ForegroundColor Cyan

    for ($i = 0; $i -lt $personas.Count; $i++) {
        $desc = Get-PersonaDescription $personas[$i]
        $label = "  [$($i + 1)] $($personas[$i])"
        if ($personas[$i] -eq $currentPersona) {
            Write-Host "$label  (active)" -ForegroundColor Green
        } else {
            Write-Host $label
        }
        Write-Host "      $desc" -ForegroundColor DarkGray
    }

    Write-Host ""
    $selection = Read-Host "  Select persona (1-$($personas.Count))"

    if ($selection -match '^\d+$' -and [int]$selection -ge 1 -and [int]$selection -le $personas.Count) {
        $Persona = $personas[[int]$selection - 1]
    } else {
        Write-Host "  Invalid selection." -ForegroundColor Red
        exit 1
    }
}

# Validate persona exists
$personaPath = "$personaRoot\$Persona\AGENTS.md"
if (-not (Test-Path $personaPath)) {
    # Fall back to old format
    $personaPath = "$personaRoot\$Persona\copilot-instructions.md"
    if (-not (Test-Path $personaPath)) {
        Write-Host "  Persona '$Persona' not found" -ForegroundColor Red
        Write-Host "  Available: $($personas -join ', ')" -ForegroundColor Yellow
        exit 1
    }
}

# Determine targets
$deployCli = $false
$deployVscode = $false

switch ($Target) {
    "cli"    { $deployCli = $true }
    "vscode" { $deployVscode = $true }
    "all"    { $deployCli = $true; $deployVscode = $true }
    "auto"   {
        $deployCli = Test-Path "$HOME\.copilot\config.json"
        $deployVscode = Test-Path "$env:APPDATA\Code\User\settings.json"
        if (-not $deployCli -and -not $deployVscode) { $deployCli = $true }
    }
}

# Deploy Layer 3 — copy persona AGENTS.md to active location(s)
if ($deployCli) {
    New-Item -ItemType Directory -Path $activeDir -Force | Out-Null
    Copy-Item -Path $personaPath -Destination $activeFile -Force
    Write-Host "  ✅ CLI: Switched to '$Persona'" -ForegroundColor Green
    Write-Host "     → $activeFile" -ForegroundColor DarkGray
}

if ($deployVscode) {
    $vscodeAgentsDir = "$env:APPDATA\Code\User\agents"
    New-Item -ItemType Directory -Path $vscodeAgentsDir -Force | Out-Null
    Copy-Item -Path $personaPath -Destination "$vscodeAgentsDir\active-persona.agent.md" -Force
    Write-Host "  ✅ VS Code: Switched to '$Persona'" -ForegroundColor Green
    Write-Host "     → $vscodeAgentsDir\active-persona.agent.md" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  Layers 1 (base) and 2 (instance rules) were not modified." -ForegroundColor DarkGray
Write-Host "  Restart Copilot CLI / reload VS Code for changes to take effect." -ForegroundColor Yellow
Write-Host ""

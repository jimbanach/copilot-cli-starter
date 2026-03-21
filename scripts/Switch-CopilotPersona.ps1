<#
.SYNOPSIS
    Switch between Copilot CLI personas (3-layer model).

.DESCRIPTION
    Copies the selected persona's persona.instructions.md to
    ~/.copilot/personas/active/.github/instructions/persona.instructions.md
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
$activeInstructionsDir = "$activeDir\.github\instructions"
$activeFile = "$activeInstructionsDir\persona.instructions.md"
$legacyActiveFile = "$activeDir\AGENTS.md"
$baseFile = "$HOME\.copilot\copilot-instructions.md"

# Helper: extract persona description from first line after "# Persona:"
function Get-PersonaDescription {
    param([string]$PersonaName)
    # Try persona.instructions.md first, fall back to AGENTS.md, then copilot-instructions.md
    $file = Join-Path $personaRoot "$PersonaName\persona.instructions.md"
    if (-not (Test-Path $file)) {
        $file = Join-Path $personaRoot "$PersonaName\AGENTS.md"
    }
    if (-not (Test-Path $file)) {
        $file = Join-Path $personaRoot "$PersonaName\copilot-instructions.md"
    }
    if (Test-Path $file) {
        # Skip frontmatter lines, find first "# Persona:" line
        $lines = Get-Content $file
        foreach ($line in $lines) {
            if ($line -match "^# Persona:\s*(.+)") { return $Matches[1] }
        }
        return "(no description)"
    }
    return "(no description)"
}

# Get available personas (dirs with persona.instructions.md, AGENTS.md, or copilot-instructions.md, excluding 'active')
$personas = Get-ChildItem -Path $personaRoot -Directory | Where-Object { $_.Name -ne 'active' } | Where-Object {
    (Test-Path "$($_.FullName)\persona.instructions.md") -or (Test-Path "$($_.FullName)\AGENTS.md") -or (Test-Path "$($_.FullName)\copilot-instructions.md")
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

# Helper: resolve persona source file (persona.instructions.md > AGENTS.md > copilot-instructions.md)
function Get-PersonaSourceFile {
    param([string]$PersonaName)
    $file = "$personaRoot\$PersonaName\persona.instructions.md"
    if (Test-Path $file) { return $file }
    $file = "$personaRoot\$PersonaName\AGENTS.md"
    if (Test-Path $file) { return $file }
    $file = "$personaRoot\$PersonaName\copilot-instructions.md"
    if (Test-Path $file) { return $file }
    return $null
}

# Check current persona by comparing active persona file (line-by-line for CRLF tolerance)
$currentPersona = $null
# Check new location first, fall back to legacy
$currentActiveFile = if (Test-Path $activeFile) { $activeFile } elseif (Test-Path $legacyActiveFile) { $legacyActiveFile } else { $null }
if ($currentActiveFile) {
    $activeLines = @(Get-Content $currentActiveFile -ErrorAction SilentlyContinue)
    $bestMatch = $null
    $bestDiffCount = [int]::MaxValue

    foreach ($p in $personas) {
        $pFile = Get-PersonaSourceFile $p
        if (-not $pFile) { continue }
        $pLines = @(Get-Content $pFile -ErrorAction SilentlyContinue)
        $diff = Compare-Object $activeLines $pLines -ErrorAction SilentlyContinue
        $diffCount = if ($diff) { $diff.Count } else { 0 }

        if ($diffCount -eq 0) {
            # Exact match
            $currentPersona = $p
            break
        } elseif ($diffCount -lt $bestDiffCount) {
            $bestMatch = $p
            $bestDiffCount = $diffCount
        }
    }

    # If no exact match but a close match exists, use it (persona was edited)
    if (-not $currentPersona -and $bestMatch -and $bestDiffCount -lt 20) {
        $currentPersona = $bestMatch
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
$personaPath = Get-PersonaSourceFile $Persona
if (-not $personaPath) {
    Write-Host "  Persona '$Persona' not found" -ForegroundColor Red
    Write-Host "  Available: $($personas -join ', ')" -ForegroundColor Yellow
    exit 1
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

# Check for unsaved edits to the current active persona before switching
if ($currentPersona -and $currentActiveFile) {
    $currentSourceFile = Get-PersonaSourceFile $currentPersona
    if ($currentSourceFile) {
        $activeLines = @(Get-Content $currentActiveFile)
        $sourceLines = @(Get-Content $currentSourceFile)
        $diff = Compare-Object $sourceLines $activeLines -ErrorAction SilentlyContinue
        if ($diff.Count -gt 0) {
            Write-Host ""
            Write-Host "  ⚠️  Active persona '$currentPersona' has unsaved edits." -ForegroundColor Yellow
            $save = Read-Host "  Save changes back to $currentPersona before switching? (Y/n, default: Y)"
            if ($save -eq "" -or $save -match '^[Yy]') {
                Copy-Item $currentActiveFile $currentSourceFile -Force
                Write-Host "  ✅ Saved edits to $currentPersona" -ForegroundColor Green
            } else {
                Write-Host "  ⏭️  Edits discarded" -ForegroundColor DarkGray
            }
        }
    }
}

# Deploy Layer 3 — copy persona file to active location(s)
if ($deployCli) {
    New-Item -ItemType Directory -Path $activeInstructionsDir -Force | Out-Null
    Copy-Item -Path $personaPath -Destination $activeFile -Force
    # Clean up legacy AGENTS.md if present
    if (Test-Path $legacyActiveFile) { Remove-Item $legacyActiveFile -Force }
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

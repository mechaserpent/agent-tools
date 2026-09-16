$ErrorActionPreference = 'Stop'

# Install agent-tools from the directory containing this script.
$Root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$HomeDir = $env:USERPROFILE
$InstallDir = if ($env:AGENT_TOOLS_INSTALL_DIR) { $env:AGENT_TOOLS_INSTALL_DIR } else { Join-Path $HomeDir '.local\share\agent-tools' }
$BinDir = if ($env:AGENT_TOOLS_BIN_DIR) { $env:AGENT_TOOLS_BIN_DIR } else { Join-Path $HomeDir '.local\bin' }
$SkillDir = if ($env:AGENT_TOOLS_SKILL_DIR) { $env:AGENT_TOOLS_SKILL_DIR } else { Join-Path $HomeDir '.agents\skills\token-efficient-debugging' }
$CodexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HomeDir '.codex' }
$ProjectDir = if ($env:AGENT_TOOLS_PROJECT_DIR) { (Resolve-Path -LiteralPath $env:AGENT_TOOLS_PROJECT_DIR).Path } else { (Get-Location).Path }
$CopilotFile = Join-Path $ProjectDir '.github\copilot-instructions.md'
$CopilotSource = Join-Path $InstallDir 'adapters\vscode-copilot\copilot-instructions.md'

function Ensure-Parent([string]$Path) {
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
}

function Assert-SafeInstallPath([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to replace existing non-link path: $Path"
        }
    }
}

function New-DirectoryLinkOrCopy([string]$Target, [string]$LinkPath) {
    Assert-SafeInstallPath $LinkPath
    if (Test-Path -LiteralPath $LinkPath) { Remove-Item -LiteralPath $LinkPath -Force -Recurse }
    Ensure-Parent $LinkPath
    try {
        New-Item -ItemType Junction -Path $LinkPath -Target $Target | Out-Null
    } catch {
        # Junction creation normally works for user-owned directories without elevation.
        # If the environment blocks it, copy the directory so installation still works.
        Write-Warning "Could not create directory junction at '$LinkPath'; falling back to a copy."
        Copy-Item -LiteralPath $Target -Destination $LinkPath -Recurse -Force
    }
}

function Find-Python {
    $candidates = @('py', 'python')
    foreach ($candidate in $candidates) {
        try {
            & $candidate -3 --version *> $null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    throw 'Python 3 was not found. Install Python 3 and ensure the py launcher or python.exe is available on PATH.'
}

$Python = Find-Python

New-Item -ItemType Directory -Force -Path $BinDir, $CodexDir | Out-Null

# Keep the installed repository linked to this clone when possible.
New-DirectoryLinkOrCopy $Root $InstallDir

# Windows command wrappers work from both PowerShell and cmd.exe.
$scriptDir = Join-Path $InstallDir 'skills\token-efficient-debugging\scripts'
$wrappers = @{
    'tkrun.cmd' = "@$env:ComSpec /d /c `"$Python -3 `"$scriptDir\tkrun.py`" %*`""
    'tkread.cmd' = "@$env:ComSpec /d /c `"$Python -3 `"$scriptDir\tkread.py`" %*`""
    'tkstats.cmd' = "@$env:ComSpec /d /c `"$Python -3 `"$scriptDir\tkstats.py`" %*`""
}
foreach ($name in $wrappers.Keys) {
    $path = Join-Path $BinDir $name
    Set-Content -LiteralPath $path -Value $wrappers[$name] -Encoding ASCII
}

# Shared skill: use a junction when available, otherwise copy it.
New-DirectoryLinkOrCopy (Join-Path $InstallDir 'skills\token-efficient-debugging') $SkillDir

# Configure Codex hooks while preserving unrelated existing settings.
$HooksFile = Join-Path $CodexDir 'hooks.json'
if (Test-Path -LiteralPath $HooksFile) {
    $hooksJson = Get-Content -LiteralPath $HooksFile -Raw | ConvertFrom-Json
} else {
    $hooksJson = [pscustomobject]@{}
}
if (-not $hooksJson.PSObject.Properties['hooks']) {
    $hooksJson | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{})
}
if (-not $hooksJson.hooks.PSObject.Properties['PreToolUse']) {
    $hooksJson.hooks | Add-Member -NotePropertyName PreToolUse -NotePropertyValue @()
}

$pre = @($hooksJson.hooks.PreToolUse) | Where-Object {
    -not ($_ -and $_.matcher -eq '^Bash$' -and (@($_.hooks) | Where-Object { $_.command -like '*token_saver.py*' }).Count -gt 0)
}
$windowsHook = "py -3 `"$InstallDir\adapters\codex\hooks\token_saver.py`""
$unixHook = "python3 `"$InstallDir/adapters/codex/hooks/token_saver.py`""
$pre += [pscustomobject]@{
    matcher = '^Bash$'
    hooks = @([pscustomobject]@{
        type = 'command'
        command = $unixHook
        commandWindows = $windowsHook
        timeout = 10
        statusMessage = 'Checking whether command output should be reduced'
    })
}
$hooksJson.hooks.PreToolUse = @($pre)
$hooksJson | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $HooksFile -Encoding UTF8

# Merge the managed Copilot instruction block without overwriting user content.
Ensure-Parent $CopilotFile
$start = '<!-- agent-tools:start -->'
$end = '<!-- agent-tools:end -->'
$block = $start + "`n" + (Get-Content -LiteralPath $CopilotSource -Raw).Trim() + "`n" + $end
if (Test-Path -LiteralPath $CopilotFile) {
    $text = Get-Content -LiteralPath $CopilotFile -Raw
} else {
    $text = ''
}
if ($text.Contains($start) -and $text.Contains($end)) {
    $before = $text.Substring(0, $text.IndexOf($start)).TrimEnd()
    $afterStart = $text.IndexOf($end) + $end.Length
    $after = $text.Substring($afterStart).TrimStart()
    $text = if ($before) { $before + "`n`n" + $block } else { $block }
    if ($after) { $text += "`n`n" + $after }
    $text += "`n"
} else {
    $text = $text.TrimEnd()
    $text = if ($text) { $text + "`n`n" + $block + "`n" } else { $block + "`n" }
}
Set-Content -LiteralPath $CopilotFile -Value $text -Encoding UTF8

Write-Host ''
Write-Host 'Installed agent-tools for Windows.'
Write-Host ''
Write-Host "Source:                  $InstallDir -> $Root"
Write-Host "CLI directory:           $BinDir"
Write-Host "  tkrun.cmd / tkread.cmd / tkstats.cmd"
Write-Host "Skill:                   $SkillDir"
Write-Host "Codex hooks:             $HooksFile"
Write-Host "VS Code Copilot:         $CopilotFile"
Write-Host ''
Write-Host "Make sure '$BinDir' is in your user PATH, then restart your terminal/VS Code."

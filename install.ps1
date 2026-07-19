# One-line installer for the Hyperagent -> OpenAI gateway (Windows PowerShell).
#   irm https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.ps1 | iex
# Installs the `hyperagent-gateway` (alias `hga`) CLI via pipx / uv / pip,
# then scaffolds %USERPROFILE%\.hyperagent-gateway\.env
#requires -Version 5
$ErrorActionPreference = 'Stop'
$Repo = 'git+https://github.com/dinhhung893/hyperagent-openai-gateway'
$HomeDir = Join-Path $env:USERPROFILE '.hyperagent-gateway'

function Have($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host 'Installing Hyperagent -> OpenAI gateway...' -ForegroundColor Cyan

if (Have 'pipx') {
    pipx install $Repo --force
} elseif (Have 'uv') {
    uv tool install $Repo
} else {
    $py = if (Have 'py') { 'py' } elseif (Have 'python') { 'python' } elseif (Have 'python3') { 'python3' } else { $null }
    if (-not $py) {
        throw 'Python not found. Install Python 3.11+ from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then re-run.'
    }
    Write-Host 'pipx/uv not found - installing with pip (user)...' -ForegroundColor Yellow
    & $py -m pip install --user --upgrade $Repo
}

# Scaffold .env
New-Item -ItemType Directory -Force -Path $HomeDir | Out-Null
$envFile = Join-Path $HomeDir '.env'
if (-not (Test-Path $envFile)) {
    $rand = -join ((48..57) + (97..102) | Get-Random -Count 12 | ForEach-Object { [char]$_ })
    @(
        'GATEWAY_UPSTREAM=mcp',
        'HYPERAGENT_MCP_URL=https://hyperagent.com/api/mcp',
        "SHIM_API_KEYS=sk-local-$rand",
        'GATEWAY_PORT=8000'
    ) | Set-Content -Path $envFile -Encoding utf8
    Write-Host "Wrote $envFile"
} else {
    Write-Host "Keeping existing $envFile"
}

Write-Host ''
Write-Host 'Done. Next steps:' -ForegroundColor Green
Write-Host '  hga login     # one-time Hyperagent sign-in'
Write-Host '  hga serve     # start the gateway on http://localhost:8000/v1'
Write-Host "  (if 'hga' is not found, use:  py -m gateway.cli serve )"

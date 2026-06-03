[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $RepoRoot "CampusGuard.spec"
$DistDir = Join-Path $RepoRoot "dist\CampusGuard"
$ExePath = Join-Path $DistDir "CampusGuard.exe"

Set-Location $RepoRoot

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found: $Python"
}

if (-not (Test-Path -LiteralPath $Spec)) {
    throw "PyInstaller spec not found: $Spec"
}

if (-not $SkipTests) {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed"
    }
}

& $Python -m py_compile campus_guard.pyw tests/test_campus_guard.py campus_guard\models.py campus_guard\config.py campus_guard\auth.py campus_guard\system.py campus_guard\battery.py campus_guard\network.py campus_guard\telegram_bot.py campus_guard\runtime.py campus_guard\ui.py
if ($LASTEXITCODE -ne 0) {
    throw "py_compile failed"
}

& $Python -m PyInstaller --noconfirm --clean $Spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller packaging failed"
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Expected executable was not created: $ExePath"
}

Copy-Item -LiteralPath (Join-Path $RepoRoot "config.example.json") -Destination (Join-Path $DistDir "config.example.json") -Force

Write-Host "Campus Guard packaged successfully:"
Write-Host $ExePath

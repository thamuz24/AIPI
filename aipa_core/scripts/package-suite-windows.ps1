param(
    [switch]$SkipCoreBuild,
    [switch]$BuildClient,
    [string]$ClientDir = "..\aipa_client",
    [string]$ControllDir = "..\aipa_controll",
    [string]$OutputDir = "..\AIPA_App"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PackageScript = Join-Path $PSScriptRoot "package-windows.ps1"
$ClientRoot = (Resolve-Path (Join-Path $ProjectRoot $ClientDir)).Path
$ControllRoot = (Resolve-Path (Join-Path $ProjectRoot $ControllDir)).Path
$ClientBuildDir = Join-Path $ClientRoot "build"
$AppImageRoot = Join-Path $ProjectRoot "release\windows\AIPA"
$AppContentDir = Join-Path $AppImageRoot "app"
$SuiteClientDir = Join-Path $AppContentDir "client"
$SuiteControllDir = Join-Path $AppContentDir "controll"
$ExportDirFull = if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    [System.IO.Path]::GetFullPath($OutputDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDir))
}

if (-not (Test-Path $PackageScript)) {
    throw "Cannot find package script: $PackageScript"
}

if (-not (Test-Path $ClientRoot)) {
    throw "Cannot find aipa_client directory: $ClientRoot"
}

if (-not (Test-Path $ControllRoot)) {
    throw "Cannot find aipa_controll directory: $ControllRoot"
}

if ($BuildClient) {
    Write-Host "Building aipa_client production assets..."
    Push-Location $ClientRoot
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $ClientBuildDir)) {
    throw "Client build folder not found: $ClientBuildDir. Run with -BuildClient or build aipa_client first."
}

Write-Host "Packaging aipa_core app image..."
& $PackageScript -Type app-image -SkipBuild:$SkipCoreBuild
if ($LASTEXITCODE -ne 0) {
    throw "package-windows.ps1 failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $AppContentDir)) {
    throw "App content directory not found: $AppContentDir"
}

if (Test-Path $SuiteClientDir) {
    Remove-Item -Path $SuiteClientDir -Recurse -Force
}
if (Test-Path $SuiteControllDir) {
    Remove-Item -Path $SuiteControllDir -Recurse -Force
}

Write-Host "Copying aipa_client build into packaged app..."
New-Item -ItemType Directory -Path $SuiteClientDir -Force | Out-Null
Copy-Item -Path (Join-Path $ClientBuildDir "*") -Destination $SuiteClientDir -Recurse -Force

Write-Host "Copying aipa_controll into packaged app..."
New-Item -ItemType Directory -Path $SuiteControllDir -Force | Out-Null

$excludeTopLevel = @(".idea", "__pycache__", "tmp", "node_modules")
Get-ChildItem -Path $ControllRoot -Force | Where-Object { $excludeTopLevel -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $SuiteControllDir $_.Name) -Recurse -Force
}

Get-ChildItem -Path $SuiteControllDir -Recurse -Directory -Force |
    Where-Object { $_.Name -in @(".idea", "__pycache__", "tmp", "node_modules") } |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $SuiteControllDir -Recurse -File -Force -Include "*.pyc" |
    Remove-Item -Force

$chatServerPath = Join-Path $SuiteControllDir "chat_server.py"
if (-not (Test-Path $chatServerPath)) {
    throw "chat_server.py not found in copied controll directory: $chatServerPath"
}

$chatServerText = Get-Content -Path $chatServerPath -Raw
if ($chatServerText -notmatch "http://localhost:8080") {
    $chatServerText = $chatServerText -replace "'http://127\.0\.0\.1:3000',\r?\n\s*\],", "'http://127.0.0.1:3000',`r`n        'http://localhost:8080',`r`n        'http://127.0.0.1:8080',`r`n    ],"
}

# chat_server.py must be UTF-8 for Python to import reliably.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($chatServerPath, $chatServerText, $utf8NoBom)

$chatServerEncoding = (Get-Content -Path $chatServerPath -Raw -Encoding UTF8)
if ($chatServerEncoding -notmatch "(?m)^#\s*-\*-\s*coding:\s*utf-8\s*-\*-\s*$") {
    $chatServerEncoding = "# -*- coding: utf-8 -*-`r`n" + $chatServerEncoding
    [System.IO.File]::WriteAllText($chatServerPath, $chatServerEncoding, $utf8NoBom)
}

$cfgPath = Join-Path $AppContentDir "AIPA.cfg"
if (-not (Test-Path $cfgPath)) {
    throw "AIPA.cfg not found: $cfgPath"
}

$cfgText = Get-Content -Path $cfgPath -Raw
if ($cfgText -notmatch "(?m)^java-options=-Daipa.desktop.enabled=true$") {
    $cfgText = $cfgText.TrimEnd() + "`r`njava-options=-Daipa.desktop.enabled=true`r`n"
    [System.IO.File]::WriteAllText($cfgPath, $cfgText, [System.Text.Encoding]::ASCII)
}

$legacyStart = Join-Path $AppImageRoot "Start-AIPA-All.bat"
$legacyStop = Join-Path $AppImageRoot "Stop-AIPA-All.bat"
if (Test-Path $legacyStart) {
    Remove-Item -Path $legacyStart -Force
}
if (Test-Path $legacyStop) {
    Remove-Item -Path $legacyStop -Force
}

if (Test-Path $ExportDirFull) {
    Remove-Item -Path $ExportDirFull -Recurse -Force
}
New-Item -ItemType Directory -Path $ExportDirFull -Force | Out-Null
Copy-Item -Path (Join-Path $AppImageRoot "*") -Destination $ExportDirFull -Recurse -Force

Write-Host ""
Write-Host "Suite packaging completed."
Write-Host "Output: $ExportDirFull"
Write-Host "Run: $(Join-Path $ExportDirFull 'AIPA.exe')"

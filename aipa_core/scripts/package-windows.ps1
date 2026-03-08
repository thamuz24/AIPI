param(
    [ValidateSet("app-image", "exe", "msi")]
    [string]$Type = "app-image",
    [string]$AppName = "AIPA",
    [string]$Vendor = "AIPA Team",
    [string]$AppVersion = "",
    [switch]$SkipBuild,
    [string]$IconPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-NormalizedVersion {
    param([string]$RawVersion)

    if ([string]::IsNullOrWhiteSpace($RawVersion)) {
        return "1.0.0"
    }

    $match = [regex]::Match($RawVersion, "(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?")
    if (-not $match.Success) {
        return "1.0.0"
    }

    $segments = @($match.Groups[1].Value)
    for ($i = 2; $i -le 4; $i++) {
        if ([string]::IsNullOrWhiteSpace($match.Groups[$i].Value)) {
            break
        }
        $segments += $match.Groups[$i].Value
    }

    return ($segments -join ".")
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$MavenWrapper = Join-Path $ProjectRoot "mvnw.cmd"
$PomPath = Join-Path $ProjectRoot "pom.xml"
$TargetDir = Join-Path $ProjectRoot "target"
$ReleaseRoot = Join-Path $ProjectRoot "release\windows"
$InputDir = Join-Path $ReleaseRoot "input"

if (-not (Test-Path $PomPath)) {
    throw "Cannot find pom.xml at $PomPath"
}

if (-not (Test-Path $MavenWrapper)) {
    throw "Cannot find Maven wrapper at $MavenWrapper"
}

$javaHome = $env:JAVA_HOME
if ([string]::IsNullOrWhiteSpace($javaHome)) {
    throw "JAVA_HOME is not set. Please set JAVA_HOME to a JDK (21+ recommended)."
}

$jpackageExe = Join-Path $javaHome "bin\jpackage.exe"
if (-not (Test-Path $jpackageExe)) {
    throw "jpackage not found at $jpackageExe. Install a full JDK and set JAVA_HOME correctly."
}

[xml]$pom = Get-Content -Path $PomPath
$pomVersion = [string]$pom.project.version
if ([string]::IsNullOrWhiteSpace($AppVersion)) {
    $AppVersion = Get-NormalizedVersion -RawVersion $pomVersion
}

if ($Type -eq "exe" -or $Type -eq "msi") {
    $hasWixV3 = $null -ne (Get-Command "light.exe" -ErrorAction SilentlyContinue) -and
        $null -ne (Get-Command "candle.exe" -ErrorAction SilentlyContinue)
    $hasWixV4Or5 = $null -ne (Get-Command "wix.exe" -ErrorAction SilentlyContinue)

    if (-not ($hasWixV3 -or $hasWixV4Or5)) {
        throw "WiX Toolset is required for -Type $Type. Install WiX and add it to PATH (https://wixtoolset.org)."
    }
}

if (-not $SkipBuild) {
    Write-Host "Building Spring Boot jar..."
    & $MavenWrapper clean package -DskipTests
}

if (-not (Test-Path $TargetDir)) {
    throw "Target directory not found: $TargetDir"
}

$jar = Get-ChildItem -Path $TargetDir -Filter "*.jar" -File |
    Where-Object { $_.Name -notmatch "(?i)(original|sources|javadoc|tests?)" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $jar) {
    throw "No runnable jar found in $TargetDir"
}

if (Test-Path $ReleaseRoot) {
    Remove-Item -Path $ReleaseRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $InputDir -Force | Out-Null
Copy-Item -Path $jar.FullName -Destination (Join-Path $InputDir $jar.Name) -Force

$args = @(
    "--type", $Type,
    "--name", $AppName,
    "--dest", $ReleaseRoot,
    "--input", $InputDir,
    "--main-jar", $jar.Name,
    "--app-version", $AppVersion,
    "--vendor", $Vendor,
    "--java-options", "-Dfile.encoding=UTF-8"
)

if (-not [string]::IsNullOrWhiteSpace($IconPath)) {
    $resolvedIconPath = (Resolve-Path $IconPath).Path
    $args += @("--icon", $resolvedIconPath)
}

if ($Type -eq "exe" -or $Type -eq "msi") {
    $args += @(
        "--win-dir-chooser",
        "--win-menu",
        "--win-shortcut",
        "--win-shortcut-prompt"
    )
}

Write-Host "Running jpackage..."
& $jpackageExe @args
if ($LASTEXITCODE -ne 0) {
    throw "jpackage failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Packaging completed."
Write-Host "Output: $ReleaseRoot"

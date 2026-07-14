<#
.SYNOPSIS
    FinAlly — start script (Windows PowerShell).
.DESCRIPTION
    Builds the Docker image if it doesn't exist (or if -Build is passed),
    then runs the container with the db volume, port mapping, and .env file.
    Idempotent: safe to run multiple times.
#>
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$ImageName = "finally"
$ContainerName = "finally-app"
$VolumeName = "finally-data"
$Port = if ($env:FINALLY_PORT) { $env:FINALLY_PORT } else { "8000" }
$EnvFile = Join-Path $ProjectRoot ".env"

Set-Location $ProjectRoot

if (-not (Test-Path $EnvFile)) {
    Write-Warning "$EnvFile not found. Copy .env.example to .env and set OPENROUTER_API_KEY."
}

# Already running? Nothing to do.
$running = docker ps --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$" -Quiet
if ($running) {
    Write-Host "FinAlly is already running at http://localhost:$Port"
    exit 0
}

$imageExists = $true
docker image inspect $ImageName *> $null
if ($LASTEXITCODE -ne 0) { $imageExists = $false }

if ($Build -or -not $imageExists) {
    Write-Host "Building $ImageName image..."
    docker build -t $ImageName .
}

# Remove a stopped leftover container from a previous run, if any.
$existing = docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$" -Quiet
if ($existing) {
    docker rm $ContainerName | Out-Null
}

docker volume create $VolumeName | Out-Null

$dockerArgs = @("run", "-d", "--name", $ContainerName, "-p", "${Port}:8000", "-v", "${VolumeName}:/app/db")
if (Test-Path $EnvFile) {
    $dockerArgs += @("--env-file", $EnvFile)
}
$dockerArgs += $ImageName

docker @dockerArgs | Out-Null

Write-Host "FinAlly is starting at http://localhost:$Port"
Start-Process "http://localhost:$Port"

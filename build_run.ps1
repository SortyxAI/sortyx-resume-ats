#!/usr/bin/env pwsh

param(
    [string]$ImageName = "sortyx-resume-ats:local",
    [string]$ContainerName = "sortyx-resume-ats-local",
    [int]$HostPort = 8000,
    [int]$ContainerPort = 8000,
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptRoot

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "docker")) {
    throw "Docker is not installed or not available on PATH."
}

foreach ($requiredFile in @("Dockerfile", "requirements.txt", "app/main.py")) {
    if (-not (Test-Path -Path $requiredFile -PathType Leaf)) {
        throw "Required project file not found: $requiredFile"
    }
}

Write-Host "SortyX Resume ATS - Local Docker Build & Run" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Project directory: $ScriptRoot" -ForegroundColor Gray

if (Test-Path ".env") {
    Write-Host ".env found and will be passed to the container." -ForegroundColor Green
} else {
    Write-Host ".env not found. Set runtime variables manually if needed." -ForegroundColor Yellow
}

$BuildArgs = @("build", "-t", $ImageName, ".")
if ($NoCache) {
    $BuildArgs = @("build", "--no-cache", "-t", $ImageName, ".")
}

Write-Host "Building image: $ImageName" -ForegroundColor Cyan
& docker @BuildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed."
}

Write-Host "Stopping any existing container named $ContainerName..." -ForegroundColor Cyan
& docker rm -f $ContainerName 2>$null | Out-Null

$RunArgs = @(
    "run",
    "-d",
    "--name", $ContainerName,
    "-p", "$HostPort`:$ContainerPort",
    "--restart", "unless-stopped"
)

if (Test-Path ".env") {
    $RunArgs += @("--env-file", ".env")
}

if (Test-Path "token.json") {
    $RunArgs += @("-v", "$ScriptRoot/token.json:/app/token.json")
} else {
    Write-Host "token.json not found; container will start without the OAuth token file." -ForegroundColor Yellow
}

if (Test-Path "client_secrets1.json") {
    $RunArgs += @("-v", "$ScriptRoot/client_secrets1.json:/app/client_secrets1.json")
} else {
    Write-Host "client_secrets1.json not found; container will start without the OAuth client file." -ForegroundColor Yellow
}

$RunArgs += $ImageName

Write-Host "Running container: $ContainerName" -ForegroundColor Cyan
& docker @RunArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker run failed."
}

$ServiceUrl = "http://localhost:$HostPort"
Write-Host "" 
Write-Host "Container started successfully." -ForegroundColor Green
Write-Host "Service URL:  $ServiceUrl" -ForegroundColor Green
Write-Host "Health check: $ServiceUrl/health" -ForegroundColor Green
Write-Host "Docs:         $ServiceUrl/docs" -ForegroundColor Green
Write-Host "" 
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  docker logs -f $ContainerName" -ForegroundColor Gray
Write-Host "  docker stop $ContainerName" -ForegroundColor Gray
Write-Host "  docker rm -f $ContainerName" -ForegroundColor Gray
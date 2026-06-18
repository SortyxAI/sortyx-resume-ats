#!/usr/bin/env pwsh

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Region = "us-central1",
    [string]$ServiceName = "sortyx-resume-ats",
    [string]$RepositoryName = "sortyx-resume-ats",
    [string]$ImageName = "sortyx-resume-ats",
    [string]$Memory = "2Gi",
    [string]$Cpu = "2",
    [string]$Timeout = "300s",
    [int]$MinInstances = 0,
    [int]$MaxInstances = 5,
    [string]$ReleaseTag,

    [string]$SpreadsheetId,
    [string]$GoogleDriveFolderId,
    [string]$AdminUsername,
    [string]$AdminPassword,
    [string]$DatabaseUrl,

    [string]$TokenFile = "token.json",
    [string]$ClientSecretsFile = "client_secrets1.json",
    [string]$TokenSecretName = "sortyx-resume-ats-token-json",
    [string]$ClientSecretsSecretName = "sortyx-resume-ats-client-secrets1-json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptRoot
    function Import-DotEnv {
        param([string]$Path)

        if (-not (Test-Path -Path $Path -PathType Leaf)) {
            return
        }

        Get-Content -Path $Path | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith("#")) {
                return
            }

            if ($line -notmatch "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
                return
            }

            $name = $matches[1]
            $value = $matches[2].Trim()

            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            if (-not [string]::IsNullOrWhiteSpace($name) -and [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($name))) {
                [Environment]::SetEnvironmentVariable($name, $value)
            }
        }
    }

    function Resolve-Setting {
        param(
            [string]$ScriptValue,
            [string]$EnvironmentName
        )

        if (-not [string]::IsNullOrWhiteSpace($ScriptValue)) {
            return $ScriptValue
        }

        $envValue = [Environment]::GetEnvironmentVariable($EnvironmentName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            return $envValue
        }

        return $null
    }
Import-DotEnv -Path ".env"

$SpreadsheetId = Resolve-Setting -ScriptValue $SpreadsheetId -EnvironmentName "SPREADSHEET_ID"
$GoogleDriveFolderId = Resolve-Setting -ScriptValue $GoogleDriveFolderId -EnvironmentName "GOOGLE_DRIVE_FOLDER_ID"
$AdminUsername = Resolve-Setting -ScriptValue $AdminUsername -EnvironmentName "ADMIN_USERNAME"
$AdminPassword = Resolve-Setting -ScriptValue $AdminPassword -EnvironmentName "ADMIN_PASSWORD"
$DatabaseUrl = Resolve-Setting -ScriptValue $DatabaseUrl -EnvironmentName "DATABASE_URL"

function Resolve-SecretName {
    param(
        [string]$Value,
        [string]$DefaultValue,
        [string]$EnvName
    )

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $Value.Trim()
    }

    $envValue = [Environment]::GetEnvironmentVariable($EnvName)
    if (-not [string]::IsNullOrWhiteSpace($envValue)) {
        return $envValue.Trim()
    }

    return $DefaultValue
}

$TokenSecretName = Resolve-SecretName -Value $TokenSecretName -DefaultValue "sortyx-resume-ats-token-json" -EnvName "TOKEN_SECRET_NAME"
$ClientSecretsSecretName = Resolve-SecretName -Value $ClientSecretsSecretName -DefaultValue "sortyx-resume-ats-client-secrets1-json" -EnvName "CLIENT_SECRETS_SECRET_NAME"

Write-Host "ENV TOKEN_SECRET_NAME: '$([Environment]::GetEnvironmentVariable('TOKEN_SECRET_NAME'))'" -ForegroundColor DarkYellow
Write-Host "ENV CLIENT_SECRETS_SECRET_NAME: '$([Environment]::GetEnvironmentVariable('CLIENT_SECRETS_SECRET_NAME'))'" -ForegroundColor DarkYellow
Write-Host "Resolved TOKEN_SECRET_NAME: '$TokenSecretName'" -ForegroundColor Magenta
Write-Host "Resolved CLIENT_SECRETS_SECRET_NAME: '$ClientSecretsSecretName'" -ForegroundColor Magenta

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Tool {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [string]$FailureMessage
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Invoke-PythonCompile {
    if (Test-Command "python") {
        Invoke-Tool -Executable "python" -Arguments @("-m", "compileall", "app") -FailureMessage "Python compileall failed. Fix the errors before deploying."
        return
    }

    if (Test-Command "py") {
        Invoke-Tool -Executable "py" -Arguments @("-3", "-m", "compileall", "app") -FailureMessage "Python compileall failed. Fix the errors before deploying."
        return
    }

    throw "Python was not found on PATH. Install Python or use the project venv before deploying."
}

function Ensure-ArtifactRegistryRepository {
    param(
        [string]$ProjectId,
        [string]$Region,
        [string]$RepositoryName
    )

    try {
        Invoke-Gcloud -Arguments @("artifacts", "repositories", "describe", $RepositoryName, "--location", $Region, "--project", $ProjectId, "--quiet")
        Write-Host "Artifact Registry repository already exists: $RepositoryName" -ForegroundColor Green
    }
    catch {
        Write-Host "Creating Artifact Registry repository: $RepositoryName" -ForegroundColor Yellow
        Invoke-Gcloud -Arguments @(
            "artifacts", "repositories", "create", $RepositoryName,
            "--repository-format=docker",
            "--location", $Region,
            "--description", "SortyX Resume ATS release images",
            "--project", $ProjectId,
            "--quiet"
        )
    }
}

function Ensure-SecretVersion {
    param(
        [string]$ProjectId,
        [string]$SecretName,
        [string]$FilePath
    )

    if (-not (Test-Path -Path $FilePath -PathType Leaf)) {
        throw "Required file not found: $FilePath"
    }

    try {
        Invoke-Gcloud -Arguments @("secrets", "describe", $SecretName, "--project", $ProjectId, "--quiet")
        Write-Host "Secret already exists: $SecretName" -ForegroundColor Green
    }
    catch {
        Write-Host "Creating secret: $SecretName" -ForegroundColor Yellow
        Invoke-Gcloud -Arguments @(
            "secrets", "create", $SecretName,
            "--replication-policy=automatic",
            "--project", $ProjectId,
            "--quiet"
        )
    }

    Write-Host "Uploading secret version from: $FilePath" -ForegroundColor Yellow
    Invoke-Gcloud -Arguments @(
        "secrets", "versions", "add", $SecretName,
        "--data-file", $FilePath,
        "--project", $ProjectId,
        "--quiet"
    )
}

function Grant-SecretAccess {
    param(
        [string]$ProjectId,
        [string]$SecretName,
        [string]$Member
    )

    Invoke-Gcloud -Arguments @(
        "secrets", "add-iam-policy-binding", $SecretName,
        "--member", $Member,
        "--role", "roles/secretmanager.secretAccessor",
        "--project", $ProjectId,
        "--quiet"
    )
}

function Grant-RepositoryAccess {
    param(
        [string]$ProjectId,
        [string]$Region,
        [string]$RepositoryName,
        [string]$Member,
        [string]$Role
    )

    Invoke-Gcloud -Arguments @(
        "artifacts", "repositories", "add-iam-policy-binding", $RepositoryName,
        "--location", $Region,
        "--member", $Member,
        "--role", $Role,
        "--project", $ProjectId,
        "--quiet"
    )
}

try {
    Write-Host "SortyX Resume ATS - Release Docker Build and GCP Deploy" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan

    foreach ($requiredCommand in @("gcloud", "docker")) {
        if (-not (Test-Command $requiredCommand)) {
            throw "$requiredCommand is not installed or not available on PATH."
        }
    }

    foreach ($requiredFile in @("Dockerfile", "requirements.txt", "app/main.py")) {
        if (-not (Test-Path -Path $requiredFile -PathType Leaf)) {
            throw "Required project file not found: $requiredFile"
        }
    }

    if (-not $SpreadsheetId) {
        throw "SPREADSHEET_ID is required. Pass -SpreadsheetId or set the environment variable."
    }

    if (-not $GoogleDriveFolderId) {
        throw "GOOGLE_DRIVE_FOLDER_ID is required. Pass -GoogleDriveFolderId or set the environment variable."
    }

    if (-not $AdminUsername) {
        throw "ADMIN_USERNAME is required. Pass -AdminUsername or set the environment variable."
    }

    if (-not $AdminPassword) {
        throw "ADMIN_PASSWORD is required. Pass -AdminPassword or set the environment variable."
    }

    if (-not (Test-Path -Path $TokenFile -PathType Leaf)) {
        throw "Required OAuth token file not found: $TokenFile"
    }

    if (-not (Test-Path -Path $ClientSecretsFile -PathType Leaf)) {
        throw "Required OAuth client file not found: $ClientSecretsFile"
    }

    if (-not $ReleaseTag) {
        try {
            $ReleaseTag = (git rev-parse --short HEAD).Trim()
        }
        catch {
            $ReleaseTag = (Get-Date -Format 'yyyyMMdd-HHmmss')
        }
    }

    $SafeReleaseTag = $ReleaseTag.ToLowerInvariant() -replace '[^a-z0-9._-]', '-'
    $LatestImageTag = "latest"

    Write-Section "Running a local Python compile check"
    Invoke-PythonCompile

    Write-Section "Configuration"
    Write-Host "Project ID:          $ProjectId"
    Write-Host "Region:              $Region"
    Write-Host "Service Name:        $ServiceName"
    Write-Host "Artifact Repo:       $RepositoryName"
    Write-Host "Image Name:          $ImageName"
    Write-Host "Release Tag:         $SafeReleaseTag"
    Write-Host "Memory:              $Memory"
    Write-Host "CPU:                 $Cpu"
    Write-Host "Timeout:             $Timeout"
    Write-Host "Min Instances:       $MinInstances"
    Write-Host "Max Instances:       $MaxInstances"

    Write-Section "Setting project"
    Invoke-Gcloud -Arguments @("config", "set", "project", $ProjectId, "--quiet")

    Write-Section "Enabling required GCP APIs"
    Invoke-Gcloud -Arguments @(
        "services", "enable",
        "run.googleapis.com",
        "artifactregistry.googleapis.com",
        "secretmanager.googleapis.com",
        "logging.googleapis.com",
        "--project", $ProjectId,
        "--quiet"
    )

    $ProjectNumber = (& gcloud projects describe $ProjectId --format="value(projectNumber)")
    if ($LASTEXITCODE -ne 0 -or -not $ProjectNumber) {
        throw "Unable to resolve project number for $ProjectId"
    }

    $RuntimeServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"
    $ServiceAgent = "service-$ProjectNumber@serverless-robot-prod.iam.gserviceaccount.com"
    $ActiveAccount = (& gcloud config get-value account 2>$null).Trim()

    if (-not $ActiveAccount) {
        throw "No active gcloud account found. Run gcloud auth login first."
    }

    Write-Host "Runtime service account: $RuntimeServiceAccount" -ForegroundColor Green
    Write-Host "Cloud Run service agent: $ServiceAgent" -ForegroundColor Green
    Write-Host "Active gcloud account:    $ActiveAccount" -ForegroundColor Green

    Write-Section "Preparing Artifact Registry"
    Ensure-ArtifactRegistryRepository -ProjectId $ProjectId -Region $Region -RepositoryName $RepositoryName
    Grant-RepositoryAccess -ProjectId $ProjectId -Region $Region -RepositoryName $RepositoryName -Member "user:$ActiveAccount" -Role "roles/artifactregistry.writer"
    Grant-RepositoryAccess -ProjectId $ProjectId -Region $Region -RepositoryName $RepositoryName -Member "serviceAccount:$RuntimeServiceAccount" -Role "roles/artifactregistry.reader"
    Grant-RepositoryAccess -ProjectId $ProjectId -Region $Region -RepositoryName $RepositoryName -Member "serviceAccount:$ServiceAgent" -Role "roles/artifactregistry.reader"

    Write-Section "Preparing Secret Manager"
    Ensure-SecretVersion -ProjectId $ProjectId -SecretName $TokenSecretName -FilePath $TokenFile
    Ensure-SecretVersion -ProjectId $ProjectId -SecretName $ClientSecretsSecretName -FilePath $ClientSecretsFile
    Grant-SecretAccess -ProjectId $ProjectId -SecretName $TokenSecretName -Member "serviceAccount:$RuntimeServiceAccount"
    Grant-SecretAccess -ProjectId $ProjectId -SecretName $ClientSecretsSecretName -Member "serviceAccount:$RuntimeServiceAccount"

    $ImageBaseUri = "$Region-docker.pkg.dev/$ProjectId/$RepositoryName/$ImageName"
    $ReleaseImageUri = "${ImageBaseUri}:$SafeReleaseTag"
    $LatestImageUri = "${ImageBaseUri}:$LatestImageTag"

    Write-Section "Building release image"
    Write-Host "Release image: $ReleaseImageUri" -ForegroundColor Green
    Invoke-Tool -Executable "docker" -Arguments @(
        "build",
        "--platform", "linux/amd64",
        "--pull",
        "--no-cache",
        "-t", $ReleaseImageUri,
        "-t", $LatestImageUri,
        "."
    ) -FailureMessage "Docker build failed."

    Write-Section "Configuring Docker authentication"
    Invoke-Gcloud -Arguments @("auth", "configure-docker", "$Region-docker.pkg.dev", "--quiet")

    Write-Section "Pushing release image"
    Invoke-Tool -Executable "docker" -Arguments @("push", $ReleaseImageUri) -FailureMessage "Docker push failed for the release image."
    Invoke-Tool -Executable "docker" -Arguments @("push", $LatestImageUri) -FailureMessage "Docker push failed for the latest image."

    $SetEnvVars = @(
        "SPREADSHEET_ID=$SpreadsheetId",
        "GOOGLE_DRIVE_FOLDER_ID=$GoogleDriveFolderId",
        "ADMIN_USERNAME=$AdminUsername",
        "ADMIN_PASSWORD=$AdminPassword"
    )

    if ($DatabaseUrl) {
        $SetEnvVars += "DATABASE_URL=$DatabaseUrl"
    }

    if ([string]::IsNullOrWhiteSpace($TokenSecretName)) {
        throw "Token secret name must be configured and not empty."
    }

    if ([string]::IsNullOrWhiteSpace($ClientSecretsSecretName)) {
        throw "Client secrets secret name must be configured and not empty."
    }

    $TokenSecretMountPath = "/run/secrets/token/token.json"
    $ClientSecretsSecretMountPath = "/run/secrets/client/client_secrets1.json"

    Write-Host "Resolved TOKEN_SECRET_NAME (final): '$TokenSecretName'" -ForegroundColor Magenta
    Write-Host "Resolved CLIENT_SECRETS_SECRET_NAME (final): '$ClientSecretsSecretName'" -ForegroundColor Magenta
    Write-Host "Token secret mount: $TokenSecretMountPath=${TokenSecretName}:latest" -ForegroundColor Green
    Write-Host "Client secrets mount: $ClientSecretsSecretMountPath=${ClientSecretsSecretName}:latest" -ForegroundColor Green

    $SecretMounts = @(
        "$TokenSecretMountPath=${TokenSecretName}:latest",
        "$ClientSecretsSecretMountPath=${ClientSecretsSecretName}:latest"
    )

    Write-Section "Deploying to Cloud Run"
    Invoke-Gcloud -Arguments @(
        "run", "deploy", $ServiceName,
        "--image", $ReleaseImageUri,
        "--platform", "managed",
        "--region", $Region,
        "--allow-unauthenticated",
        "--service-account", $RuntimeServiceAccount,
        "--port", "9000",
        "--memory", $Memory,
        "--cpu", $Cpu,
        "--timeout", $Timeout,
        "--min-instances", $MinInstances,
        "--max-instances", $MaxInstances,
        "--revision-suffix", $SafeReleaseTag,
        "--set-env-vars", ($SetEnvVars -join ","),
        "--update-secrets", ($SecretMounts -join ","),
        "--project", $ProjectId,
        "--quiet"
    )

    $ServiceUrl = (& gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $ServiceUrl) {
        throw "Deployment completed, but the service URL could not be resolved."
    }

    Write-Section "Deployment complete"
    Write-Host "Service URL:  $ServiceUrl" -ForegroundColor Green
    Write-Host "Health check: $ServiceUrl/health" -ForegroundColor Green
    Write-Host "Admin page:   $ServiceUrl/admin" -ForegroundColor Green
    Write-Host "Docs:         $ServiceUrl/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Test the health endpoint and confirm the secrets are mounted." -ForegroundColor Gray
    Write-Host "2. Submit a sample application to verify /apply works in Cloud Run." -ForegroundColor Gray
    Write-Host "3. Use gcloud run logs tail $ServiceName --region $Region for troubleshooting." -ForegroundColor Gray
}
catch {
    Write-Host ""
    Write-Host "Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location $ScriptRoot
}
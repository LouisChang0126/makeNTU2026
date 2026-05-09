# Deploy linebot to Cloud Run.
#
# Usage:
#   cd linebot
#   .\deploy.ps1
#
# Steps:
#   1. Locate gcloud (PATH or default install dir)
#   2. Wipe local __pycache__ (defense-in-depth; .gcloudignore also excludes it)
#   3. Regenerate .env.yaml from .env (skip PORT — Cloud Run injects its own)
#   4. gcloud run deploy

$ErrorActionPreference = "Stop"

$SERVICE = "makentu2026-linebot"
$REGION  = "asia-east1"
$FUNC    = "linebot"
$PROJECT = "trim-karma-391206"

# 1. gcloud
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    $candidate = "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path "$candidate\gcloud.cmd") {
        $env:Path = "$candidate;$env:Path"
        Write-Host "[deploy] added $candidate to PATH"
    } else {
        throw "gcloud not found. install Google Cloud SDK or add it to PATH."
    }
}

Set-Location -Path $PSScriptRoot

# 2. clean __pycache__
$pyc = Join-Path $PSScriptRoot "__pycache__"
if (Test-Path $pyc) {
    Remove-Item -Recurse -Force $pyc
    Write-Host "[deploy] removed local __pycache__"
}

# 3. regenerate .env.yaml
$envFile  = Join-Path $PSScriptRoot ".env"
$yamlFile = Join-Path $PSScriptRoot ".env.yaml"
if (-not (Test-Path $envFile)) {
    throw ".env not found at $envFile — copy from .env.example and fill in values."
}

$skip = @("PORT")
$lines = @()
Get-Content $envFile -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.*)$') {
        $k = $Matches[1]
        if ($skip -contains $k) { return }
        $v = $Matches[2].Trim().Trim('"')
        $v = $v -replace '\\','\\' -replace '"','\"'
        $lines += "${k}: `"$v`""
    }
}
Set-Content -Path $yamlFile -Value $lines -Encoding UTF8
Write-Host "[deploy] wrote $($lines.Count) keys to .env.yaml"

# 4. deploy
Write-Host "[deploy] deploying $SERVICE to $REGION (project $PROJECT)..."
gcloud run deploy $SERVICE `
    --source=. `
    --function=$FUNC `
    --region=$REGION `
    --project=$PROJECT `
    --allow-unauthenticated `
    --env-vars-file=.env.yaml `
    --quiet

if ($LASTEXITCODE -ne 0) {
    throw "gcloud deploy failed with exit code $LASTEXITCODE"
}

Write-Host "[deploy] done."

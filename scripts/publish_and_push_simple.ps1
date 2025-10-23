param(
  [Parameter(Mandatory=$true)][string]$Version,
  [string]$ExePath = "dist\INAT-Solutions.exe",
  [string]$PublicRepo = "valdrinhaxhimurati/INAT-Solutions-Updates",
  [string]$Branch = "gh-pages",
  [string]$ExeName = "INAT-Solutions.exe",
  [string]$PublishToken = $env:PUBLISH_TOKEN
)

if (-not (Test-Path $ExePath)) {
  Write-Error "Exe nicht gefunden: $ExePath"
  exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $scriptDir "out"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -Path $out -ItemType Directory | Out-Null

$targetExe = Join-Path $out $ExeName
Copy-Item -Path $ExePath -Destination $targetExe -Force
$hash = Get-FileHash -Path $targetExe -Algorithm SHA256
$sha = $hash.Hash.ToUpper()
Write-Host "SHA256: $sha"

$parts = $PublicRepo.Split('/')
if ($parts.Length -lt 2) { Write-Error "PublicRepo muss 'owner/repo' sein."; exit 1 }
$owner = $parts[0]; $repo = $parts[1]
$url = "https://$owner.github.io/$repo/$ExeName"
$meta = @{ version = $Version; url = $url; sha256 = $sha }
$meta | ConvertTo-Json -Depth 3 | Out-File -FilePath (Join-Path $out "version.json") -Encoding utf8

$cloneUrl = if ($PublishToken) { "https://x-access-token:$PublishToken@github.com/$PublicRepo.git" } else { "https://github.com/$PublicRepo.git" }
$pubdir = Join-Path $scriptDir "pubrepo"
if (Test-Path $pubdir) { Remove-Item $pubdir -Recurse -Force }

Write-Host "Cloning $PublicRepo (branch $Branch)..."
& git clone --single-branch --branch $Branch $cloneUrl $pubdir 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Branch $Branch existiert vermutlich nicht — erstelle $Branch..."
  & git clone $cloneUrl $pubdir
  Push-Location $pubdir
  & git checkout --orphan $Branch
  & git rm -rf . 2>$null
  & git commit --allow-empty -m "Create $Branch" 2>$null
  & git push origin $Branch 2>$null
  Pop-Location
  Remove-Item -Recurse -Force $pubdir
  & git clone --single-branch --branch $Branch $cloneUrl $pubdir
}

Copy-Item -Path (Join-Path $out "*") -Destination $pubdir -Recurse -Force
Push-Location $pubdir
& git config user.email "ci@github-actions"
& git config user.name "CI Publisher"
& git add -A

# git commit returns non-zero when no changes; handle explicitly
$null = & git commit -m "Publish $Version" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Keine Änderungen zu committen" }

& git push origin $Branch
Pop-Location

Remove-Item -Recurse -Force $out
Write-Host "Fertig: https://$owner.github.io/$repo/version.json"
<#
.SYNOPSIS
    Erstellt/Aktualisiert ein GitHub-Release und die version.json im öffentlichen Update-Repo.
.DESCRIPTION
    Dieses Skript automatisiert den gesamten Release-Prozess:
    1. Stellt sicher, dass ein Release-Tag im öffentlichen 'INAT-Solutions-Updates'-Repository existiert.
    2. Lädt die Setup-Datei als Asset hoch (überschreibt sie, falls vorhanden).
    3. Berechnet den SHA256-Hash der Setup-Datei.
    4. Erstellt/Aktualisiert die 'version.json' mit den neuen Informationen.
    5. Pusht die aktualisierte 'version.json' zurück ins Update-Repository.
.PARAMETER Version
    Der Name des Git-Tags für das Release (z.B. "v0.9.0.3").
.PARAMETER FilePath
    Der Pfad zur Setup-Datei (z.B. ".\installer\output\INAT Solutions Setup.exe").
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Version,

    [Parameter(Mandatory=$true)]
    [string]$FilePath
)

# --- Konfiguration ---
$publicRepo = "valdrinhaxhimurati/INAT-Solutions-Updates"
$publicRepoUrl = "https://github.com/$publicRepo.git"

# --- Prüfungen ---
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) ist nicht installiert. Bitte installieren Sie es von https://cli.github.com/"
    exit 1
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git ist nicht installiert oder nicht im PATH."
    exit 1
}

$fullFilePath = (Resolve-Path -Path $FilePath).Path
if (-not (Test-Path -Path $fullFilePath -PathType Leaf)) {
    Write-Error "Die Datei '$fullFilePath' wurde nicht gefunden."
    exit 1
}

# --- Schritt 1: Sicherstellen, dass das Release existiert ---
Write-Host "1/5: Prüfe, ob Release '$Version' im Repository '$publicRepo' existiert..." -ForegroundColor Cyan
$releaseExists = $false
try {
    gh release view $Version --repo $publicRepo --json tagName --jq .tagName > $null
    $releaseExists = $true
}
catch {
    # gh release view wirft einen Fehler, wenn das Release nicht existiert, das ist ok.
    $releaseExists = $false
}

if ($releaseExists) {
    Write-Host "Release '$Version' existiert bereits. Fahre fort."
}
else {
    Write-Host "Release '$Version' wird neu erstellt..."
    try {
        gh release create $Version --repo $publicRepo --title "Release $Version" --generate-notes
        if ($LASTEXITCODE -ne 0) { throw "gh release create fehlgeschlagen" }
        Write-Host "Release '$Version' wurde erfolgreich erstellt." -ForegroundColor Green
    }
    catch {
        Write-Error "Fehler beim Erstellen des GitHub-Releases."
        exit 1
    }
}

# --- Schritt 2: Setup-Datei hochladen (wichtigster Schritt) ---
Write-Host "2/5: Lade Setup-Datei hoch..." -ForegroundColor Cyan
try {
    # --clobber überschreibt die Datei, falls sie bereits existiert
    gh release upload $Version $fullFilePath --repo $publicRepo --clobber
    if ($LASTEXITCODE -ne 0) { throw "gh release upload fehlgeschlagen" }
    Write-Host "Setup-Datei wurde erfolgreich hochgeladen." -ForegroundColor Green
}
catch {
    Write-Error "Fehler beim Hochladen der Setup-Datei."
    exit 1
}

# --- Schritt 3: SHA256-Hash berechnen ---
Write-Host "3/5: Berechne SHA256-Hash für die Setup-Datei..." -ForegroundColor Cyan
$sha256 = (Get-FileHash -Path $fullFilePath -Algorithm SHA256).Hash.ToLower()
Write-Host "SHA256: $sha256"

# --- Schritt 4: version.json aktualisieren ---
Write-Host "4/5: Aktualisiere 'version.json' im Repository '$publicRepo'..." -ForegroundColor Cyan
$tempDir = Join-Path $env:TEMP "inat-updates-repo"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
git clone $publicRepoUrl $tempDir

$versionJsonPath = Join-Path $tempDir "version.json"
$installerFilename = Split-Path -Path $fullFilePath -Leaf
$downloadUrl = "https://github.com/$publicRepo/releases/download/$Version/$installerFilename"

$versionData = @{
    version = $Version.TrimStart('v');
    url = $downloadUrl;
    sha256 = $sha256;
    filename = $installerFilename
}

$versionData | ConvertTo-Json | Set-Content -Path $versionJsonPath

# --- Schritt 5: Änderungen an version.json pushen ---
Write-Host "5/5: Pushe die neue 'version.json'..." -ForegroundColor Cyan
Push-Location $tempDir
git config user.name "GitHub Actions"
git config user.email "actions@github.com"
git add version.json
git commit -m "Update version.json to $Version"
git push
Pop-Location

# --- Aufräumen ---
Remove-Item -Recurse -Force $tempDir

Write-Host "Update-Prozess erfolgreich abgeschlossen!" -ForegroundColor Green
# Arbeitsverzeichnis: Projekt-Root
cd "C:\Users\V.Haxhimurati\Documents\GitHub Repository\INAT-Solutions"

# Pfad zur EXE
$exe = "C:\Users\V.Haxhimurati\Documents\GitHub Repository\INAT-Solutions\dist\INAT-Solutions\INAT-Solutions.exe"

# SHA256 berechnen
$sha = (Get-FileHash -Path $exe -Algorithm SHA256).Hash
Write-Host "SHA256:" $sha

# gh-pages Repo klonen (einziger Branch gh-pages)
git clone --single-branch --branch gh-pages https://github.com/valdrinhaxhimurati/INAT-Solutions-Updates.git tmp-gh
if ($LASTEXITCODE -ne 0) { Write-Error "Clone fehlgeschlagen"; exit 1 }

# EXE kopieren und version.json erzeugen
Copy-Item $exe -Destination ".\tmp-gh\INAT-Solutions.exe" -Force
$version = "v0.8.6.4"   # passe an
$json = @{ version = $version; url = "https://valdrinhaxhimurati.github.io/INAT-Solutions-Updates/INAT-Solutions.exe"; sha256 = $sha } | ConvertTo-Json
$json | Out-File -Encoding utf8 ".\tmp-gh\version.json"

# Commit & Push
Set-Location .\tmp-gh
git add INAT-Solutions.exe version.json
git commit -m "Publish $version"
git push origin gh-pages

# Aufräumen
Set-Location ..
Remove-Item -Recurse -Force .\tmp-gh
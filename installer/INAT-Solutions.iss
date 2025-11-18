#define MyAppName "INAT Solutions"
#define MyAppVersion "0.9.0.2"
#define MyAppPublisher "INAT Solutions"
#define MyAppExeName "INAT-Solutions.exe"
#define MySourceDir "..\dist\INAT-Solutions"
#define MyAssetsDir ".\assets"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
; --- KORREKTUR: Standard-Installationspfad für 64-Bit-Anwendungen ---
DefaultDirName={autopf64}\{#MyAppName}
; --- KORREKTUR: Admin-Rechte für die Installation in Program Files anfordern ---
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
SetupLogging=yes
DisableProgramGroupPage=yes
ShowLanguageDialog=yes
SetupIconFile={#MyAssetsDir}\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Ausgabeverzeichnis und Dateiname so setzen, dass CI die Datei unter dist/ findet
OutputDir=dist
OutputBaseFilename=INAT-Solutions-Setup

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Dirs]
; Zentraler Datenordner für alle Benutzer. Wird bei Updates NICHT gelöscht.
; Permissions: users-modify -> Stellt sicher, dass normale Benutzer hier schreiben können.
Name: "{commonappdata}\INAT Solutions\data"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{commonappdata}\INAT Solutions\logs"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
; App-Binaries in das Installationsverzeichnis kopieren.
; WICHTIG: Keine Entwickler-Datenbanken oder Konfigs mitliefern.
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; \
  Excludes: "*.db;*.sqlite;*.log;config.json"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

; --- ENTFERNT: [InstallDelete] ---
; Diese Sektion wurde entfernt, um Datenverlust bei Updates zu verhindern.
; Inno Setup überschreibt standardmäßig nur die alten Programmdateien.

[UninstallDelete]
; Beim Deinstallieren den Datenordner nur löschen, wenn der Benutzer zustimmt.
Type: filesandordirs; Name: "{commonappdata}\{#MyAppName}"

; --- ENTFERNT: [Code] Sektion ---
; Die Splash-Screen-Logik wurde entfernt. Dies sollte von der Anwendung selbst gehandhabt werden.
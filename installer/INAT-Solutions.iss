#define MyAppName "INAT Solutions"
#define MyAppVersion "0.8.6.5"
#define MyAppPublisher "INAT Solutions"
#define MyAppExeName "INAT-Solutions.exe"
#define MySourceDir "..\dist\INAT-Solutions"
#define MyAssetsDir ".\assets"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\{#MyAppName}  
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
SetupLogging=yes
DisableProgramGroupPage=yes
ShowLanguageDialog=yes
SetupIconFile={#MyAssetsDir}\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputBaseFilename=INAT Solutions Setup  

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Dirs]
; Zentraler Datenordner (schreibbar, leer starten)
Name: "{commonappdata}\INAT Solutions\data"; Permissions: users-modify; Flags: uninsalwaysuninstall
Name: "{commonappdata}\INAT Solutions\logs"; Permissions: users-modify; Flags: uninsalwaysuninstall

[Files]
; App-Binaries, aber KEINE DBs/Einstellungen mitliefern
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; \
  Excludes: "*.db;*.sqlite;*.mdb;*.ldf;*.ndf;*.log;*.json;*.yml;*.yaml;*.ini"

; Optional: leere Default-Config (falls App sie erwartet)
; Source: ".\installer\assets\empty.json"; DestDir: "{commonappdata}\{#MyAppName}\data"; DestName: "config.json"; Flags: ignoreversion overwritereadonly
Source: "{#MyAssetsDir}\splash-de.bmp"; Flags: dontcopy
Source: "{#MyAssetsDir}\splash-en.bmp"; Flags: dontcopy

[InstallDelete]
; Vor Installation alles Alte entfernen (DBs/Einstellungen)
Type: files; Name: "{app}\*.db"
Type: files; Name: "{app}\*.sqlite"
Type: files; Name: "{app}\*.json"
Type: files; Name: "{app}\*.ini"
Type: files; Name: "{commonappdata}\{#MyAppName}\data\*.*"
Type: files; Name: "{localappdata}\{#MyAppName}\data\*.*"
Type: files; Name: "{userappdata}\{#MyAppName}\data\*.*"

[UninstallDelete]
; Beim Deinstallieren Datenordner komplett entfernen
Type: filesandordirs; Name: "{commonappdata}\{#MyAppName}"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Icons]
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Code]
#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif

const
  GWL_EXSTYLE   = -20;
  WS_EX_LAYERED = $00080000;
  LWA_ALPHA     = $00000002;

function GetWindowLong(hWnd: HWND; nIndex: Integer): Longint;
  external 'GetWindowLong{#AW}@user32.dll stdcall';
function SetWindowLong(hWnd: HWND; nIndex: Integer; dwNewLong: Longint): Longint;
  external 'SetWindowLong{#AW}@user32.dll stdcall';
function SetLayeredWindowAttributes(hWnd: HWND; crKey: Longint; bAlpha: Byte; dwFlags: Longint): Boolean;
  external 'SetLayeredWindowAttributes@user32.dll stdcall';
function GetSystemMetrics(nIndex: Integer): Integer;
  external 'GetSystemMetrics@user32.dll stdcall';

var
  SplashForm: TSetupForm;
  SplashImg: TBitmapImage;

procedure FadeOutSplash;
var i: Integer;
begin
  if not Assigned(SplashForm) then Exit;
  for i := 255 downto 0 do begin
    if (i mod 13) = 0 then begin
      SetWindowLong(SplashForm.Handle, GWL_EXSTYLE, GetWindowLong(SplashForm.Handle, GWL_EXSTYLE) or WS_EX_LAYERED);
      SetLayeredWindowAttributes(SplashForm.Handle, 0, i, LWA_ALPHA);
      Sleep(25);
    end;
  end;
end;

procedure CloseSplash;
begin
  if Assigned(SplashForm) then begin
    FadeOutSplash;
    SplashForm.Close;
    SplashForm.Free;
    SplashForm := nil;
  end;
end;

procedure ShowSplash;
var
  SplashFile, SplashPath: string;
  Bmp: TBitmap; W, H, SW, SH: Integer;
begin
  if ActiveLanguage = 'de' then SplashFile := 'splash-de.bmp' else SplashFile := 'splash-en.bmp';
  ExtractTemporaryFile(SplashFile);
  SplashPath := ExpandConstant('{tmp}\' + SplashFile);

  Bmp := TBitmap.Create;
  try
    Bmp.LoadFromFile(SplashPath);
    W := Bmp.Width; H := Bmp.Height;
  finally
    Bmp.Free;
  end;

  SW := GetSystemMetrics(0); SH := GetSystemMetrics(1);

  SplashForm := CreateCustomForm;
  SplashForm.BorderStyle := bsNone;
  SplashForm.Color := clWhite;
  SplashForm.SetBounds((SW - W) div 2, (SH - H) div 2, W, H);

  SetWindowLong(SplashForm.Handle, GWL_EXSTYLE, GetWindowLong(SplashForm.Handle, GWL_EXSTYLE) or WS_EX_LAYERED);
  SetLayeredWindowAttributes(SplashForm.Handle, 0, 255, LWA_ALPHA);

  SplashImg := TBitmapImage.Create(SplashForm);
  SplashImg.Parent := SplashForm;
  SplashImg.SetBounds(0, 0, W, H);
  SplashImg.Stretch := False;
  SplashImg.Bitmap.LoadFromFile(SplashPath);

  SplashForm.Show;
  SplashForm.Refresh;
  Sleep(5000);
  CloseSplash;
end;

function InitializeSetup: Boolean;
begin
  ExtractTemporaryFile('splash-de.bmp');
  ExtractTemporaryFile('splash-en.bmp');
  Result := True;
end;

procedure InitializeWizard;
begin
  ShowSplash;  // Splash nach Sprachauswahl anzeigen (sprachspezifischer Text)
end;
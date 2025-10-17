#define MyAppName "INAT Solutions"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "INAT Solutions"
#define MyAppExeName "INAT Solutions.exe"
#define MySourceDir "..\dist\INAT Solutions"
#define MyAssetsDir ".\assets"
#define BrandPrimary "#26A69A"
#define BrandText    "#333333"
#define BrandSubText "#666666"

[Setup]
AppId={{1A0AB0E2-8A5D-4B38-8C2C-1C2F91C1D8E3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=INAT-Solutions-Setup-{#MyAppVersion}
SetupIconFile={#MySourceDir}\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
UsePreviousAppDir=yes
SetupLogging=yes
DisableReadyMemo=no
WizardImageFile={#MyAssetsDir}\wizard-large.bmp
WizardSmallImageFile={#MyAssetsDir}\wizard-small.bmp

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
de.WelcomeLabel1=Willkommen beim Setup von {#MyAppName}
de.WelcomeLabel2=Dieses Programm führt Sie durch die Installation. Klicken Sie auf „Weiter“, um fortzufahren.

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#MyAssetsDir}\header.bmp"; Flags: dontcopy

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: unchecked

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[Code]
var TopPanel: TPanel; TopLogo: TBitmapImage;

function HexToInt(S: string): Integer; begin Result := StrToIntDef('$' + S, 0); end;
function MakeColor(R, G, B: Integer): TColor; begin Result := (R) or (G shl 8) or (B shl 16); end;
function HexColorToTColor(Hex: string): TColor;
var R, G, B: Integer;
begin
  if (Length(Hex) = 7) and (Hex[1] = '#') then begin
    R := HexToInt(Copy(Hex, 2, 2)); G := HexToInt(Copy(Hex, 4, 2)); B := HexToInt(Copy(Hex, 6, 2));
    Result := MakeColor(R, G, B);
  end else Result := clBtnFace;
end;

procedure ApplyBranding;
var cPrimary, cText, cSub: TColor;
begin
  cPrimary := HexColorToTColor('{#BrandPrimary}');
  cText := HexColorToTColor('{#BrandText}');
  cSub := HexColorToTColor('{#BrandSubText}');

  WizardForm.Color := clWhite;
  WizardForm.PageNameLabel.Font.Color := cText;
  WizardForm.PageDescriptionLabel.Font.Color := cSub;

  TopPanel := TPanel.Create(WizardForm);
  TopPanel.Parent := WizardForm;
  TopPanel.SetBounds(0, 0, WizardForm.ClientWidth, ScaleY(44));
  TopPanel.Color := cPrimary; TopPanel.BevelOuter := bvNone;
  TopPanel.Anchors := [akLeft, akTop, akRight];

  TopLogo := TBitmapImage.Create(WizardForm);
  TopLogo.Parent := TopPanel;
  try
    ExtractTemporaryFile('header.bmp');
    TopLogo.Bitmap.LoadFromFile(ExpandConstant('{tmp}\header.bmp'));
    TopLogo.Left := ScaleX(8); TopLogo.Top := ScaleY(6);
  except end;
end;

procedure InitializeWizard;
begin
  ApplyBranding;
end;
#define MyAppName "INAT Solutions"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "INAT Solutions"
#define MyAppExeName "INAT Solutions.exe"
#define MySourceDir "..\dist\INAT Solutions"
#define MyAssetsDir ".\assets"

#define BrandPrimary   "#4a6fa5"
#define TextPrimary    "#333333"
#define TextSecondary  "#666666"

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
WizardResizable=yes
WizardSizePercent=120
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UsePreviousAppDir=yes
SetupLogging=yes
WizardImageFile={#MyAssetsDir}\wizard-large.bmp
WizardSmallImageFile={#MyAssetsDir}\wizard-small.bmp
DisableWelcomePage=no

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#MyAssetsDir}\header.bmp"; Flags: dontcopy
Source: "{#MyAssetsDir}\welcome-logo.bmp"; Flags: dontcopy

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  HeaderPanel: TPanel;
  HeaderImg: TBitmapImage;
  WelcomeLogoImg: TBitmapImage;
  WelcomeTitleLabel, WelcomeSubLabel: TLabel;

function HexToInt(S: string): Integer; begin Result := StrToIntDef('$' + S, 0); end;
function MakeColor(R, G, B: Integer): TColor; begin Result := (R) or (G shl 8) or (B shl 16); end;
function HexToTColor(Hex: string): TColor;
var R, G, B: Integer;
begin
  if (Length(Hex) = 7) and (Hex[1] = '#') then begin
    R := HexToInt(Copy(Hex, 2, 2)); G := HexToInt(Copy(Hex, 4, 2)); B := HexToInt(Copy(Hex, 6, 2));
    Result := MakeColor(R, G, B);
  end else Result := clBtnFace;
end;

procedure CreateHeader;
begin
  HeaderPanel := TPanel.Create(WizardForm);
  HeaderPanel.Parent := WizardForm;
  HeaderPanel.SetBounds(0, 0, WizardForm.ClientWidth, ScaleY(70));
  HeaderPanel.BevelOuter := bvNone;
  HeaderPanel.Color := clWhite;
  HeaderPanel.Anchors := [akLeft, akTop, akRight];

  HeaderImg := TBitmapImage.Create(WizardForm);
  HeaderImg.Parent := HeaderPanel;
  try
    ExtractTemporaryFile('header.bmp');
    HeaderImg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\header.bmp'));
    HeaderImg.Left := 0; HeaderImg.Top := 0;
    HeaderImg.Width := HeaderPanel.Width;
    HeaderImg.Height := HeaderPanel.Height;
    HeaderImg.Stretch := True;
    HeaderImg.Anchors := [akLeft, akTop, akRight];
  except end;
end;

procedure CreateWelcomePage;
var
  cText, cTextSub: TColor;
begin
  cText := HexToTColor('{#TextPrimary}');
  cTextSub := HexToTColor('{#TextSecondary}');

  WizardForm.WelcomeLabel1.Visible := False;
  WizardForm.WelcomeLabel2.Visible := False;

  { Text links }
  WelcomeTitleLabel := TLabel.Create(WizardForm);
  WelcomeTitleLabel.Parent := WizardForm.WelcomePage;
  WelcomeTitleLabel.Caption := 'Willkommen bei' + #13#10 + '{#MyAppName}';
  WelcomeTitleLabel.Font.Name := 'Segoe UI';
  WelcomeTitleLabel.Font.Size := 22;
  WelcomeTitleLabel.Font.Style := [fsBold];
  WelcomeTitleLabel.Font.Color := cText;
  WelcomeTitleLabel.Left := ScaleX(40);
  WelcomeTitleLabel.Top := ScaleY(100);
  WelcomeTitleLabel.AutoSize := True;

  WelcomeSubLabel := TLabel.Create(WizardForm);
  WelcomeSubLabel.Parent := WizardForm.WelcomePage;
  WelcomeSubLabel.Caption := 'Dieses Setup führt Sie durch die Installation.' + #13#10 + 'Klicken Sie auf „Weiter", um fortzufahren.';
  WelcomeSubLabel.Font.Name := 'Segoe UI';
  WelcomeSubLabel.Font.Size := 10;
  WelcomeSubLabel.Font.Color := cTextSub;
  WelcomeSubLabel.Left := ScaleX(40);
  WelcomeSubLabel.Top := WelcomeTitleLabel.Top + WelcomeTitleLabel.Height + ScaleY(24);
  WelcomeSubLabel.AutoSize := True;

  { Logo rechts }
  WelcomeLogoImg := TBitmapImage.Create(WizardForm);
  WelcomeLogoImg.Parent := WizardForm.WelcomePage;
  try
    ExtractTemporaryFile('welcome-logo.bmp');
    WelcomeLogoImg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\welcome-logo.bmp'));
    WelcomeLogoImg.Left := WizardForm.WelcomePage.Width - ScaleX(300) - ScaleX(40);
    WelcomeLogoImg.Top := ScaleY(80);
    WelcomeLogoImg.Width := ScaleX(300);
    WelcomeLogoImg.Height := ScaleY(300);
    WelcomeLogoImg.Stretch := True;
    WelcomeLogoImg.Anchors := [akTop, akRight];
  except end;
end;

procedure AdjustPagePositions;
begin
  WizardForm.InnerPage.Top := HeaderPanel.Height + ScaleY(12);
  WizardForm.InnerPage.Height := WizardForm.InnerPage.Height - HeaderPanel.Height - ScaleY(12);
end;

procedure ApplyBranding;
var cText, cTextSub: TColor;
begin
  cText := HexToTColor('{#TextPrimary}');
  cTextSub := HexToTColor('{#TextSecondary}');

  WizardForm.Color := clWhite;
  WizardForm.Bevel.Visible := False;

  CreateHeader;
  CreateWelcomePage;
  AdjustPagePositions;

  WizardForm.PageNameLabel.Font.Name := 'Segoe UI';
  WizardForm.PageNameLabel.Font.Size := 14;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Color := cText;

  WizardForm.PageDescriptionLabel.Font.Name := 'Segoe UI';
  WizardForm.PageDescriptionLabel.Font.Size := 9;
  WizardForm.PageDescriptionLabel.Font.Color := cTextSub;

  WizardForm.NextButton.Font.Name := 'Segoe UI';
  WizardForm.NextButton.Font.Style := [fsBold];
  WizardForm.BackButton.Font.Name := 'Segoe UI';
  WizardForm.CancelButton.Font.Name := 'Segoe UI';
end;

procedure InitializeWizard;
begin
  ApplyBranding;
end;
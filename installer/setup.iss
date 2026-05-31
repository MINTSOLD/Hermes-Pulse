; Hermes Pulse Installer - Inno Setup Script
; 下载 Inno Setup: https://jrsoftware.org/isinfo.php

#define MyAppName "Hermes Pulse"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MINTSOLD"
#define MyAppURL "https://github.com/MINTSOLD/hermes-gui"
#define MyAppExeName "hermes_gui.py"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Hermes Agent
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=HermesPulse-Setup-{#MyAppVersion}
SetupIconFile=..\hermes.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\hermes_gui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app.js"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\styles.css"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\index.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hermes-logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hermes.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hermes-titlebar.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start_config_server.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "hermes_gui.py"; WorkingDir: "{app}"; IconFilename: "{app}\hermes.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "hermes_gui.py"; WorkingDir: "{app}"; IconFilename: "{app}\hermes.ico"; Tasks: desktopicon

[Run]
Filename: "pythonw.exe"; Parameters: "hermes_gui.py"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Check Python 3.11+ is installed
function IsPythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if not IsPythonInstalled then
  begin
    if MsgBox('Hermes Pulse 需要 Python 3.11+ 才能运行。'#13#10#13#10'是否继续安装？', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

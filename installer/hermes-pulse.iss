; ══════════════════════════════════════════
;  Hermes Pulse — Inno Setup 安装脚本
;  编译: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" hermes-pulse.iss
; ══════════════════════════════════════════

[Setup]
AppName=Hermes Pulse
AppVersion=1.0
AppPublisher=MINTSOLD
DefaultDirName={autopf}\Hermes Pulse
DefaultGroupName=Hermes Pulse
OutputDir=..
eleases
OutputBaseFilename=HermesPulse-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\hermes.ico
UninstallDisplayIcon={app}\hermes.ico
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"

[Files]
; 主程序文件
Source: "..\hermes_gui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\index.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\styles.css"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app.js"; DestDir: "{app}"; Flags: ignoreversion

; 图标和资源
Source: "..\hermes-logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hermes.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hermes-titlebar.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单
Name: "{group}\Hermes Pulse"; Filename: "pythonw.exe"; Parameters: """{app}\hermes_gui.py"""; IconFilename: "{app}\hermes.ico"
Name: "{group}\卸载 Hermes Pulse"; Filename: "{uninstallexe}"

; 桌面快捷方式（可选）
Name: "{autodesktop}\Hermes Pulse"; Filename: "pythonw.exe"; Parameters: """{app}\hermes_gui.py"""; IconFilename: "{app}\hermes.ico"; Tasks: desktopicon

[Run]
; 安装后运行 Python 依赖安装
Filename: "python"; Parameters: "-m pip install pywebview pystray Pillow --quiet"; StatusMsg: "安装运行环境..."; Flags: runhidden waituntilterminated

; 询问是否立即启动
Filename: "pythonw.exe"; Parameters: """{app}\hermes_gui.py"""; Description: "立即启动 Hermes Pulse"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// 检测 Python 是否已安装
function IsPythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// 安装前检查
function InitializeSetup: Boolean;
begin
  Result := True;
  if not IsPythonInstalled then
  begin
    if MsgBox('未检测到 Python 3.11+，是否继续安装？' + #13#10 + 
              '安装后需要手动安装 Python 才能运行。', 
              mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

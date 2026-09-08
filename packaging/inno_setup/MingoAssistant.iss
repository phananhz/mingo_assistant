#define MyAppName "Min Assistant"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Min Assistant"
#define MyAppExeName "MinAssistant.exe"

[Setup]
AppId={{A0B9D83B-2BF7-4A3B-A6F2-6F73E1D9A101}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Min Assistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir=..\..\dist\installer
OutputBaseFilename=MinAssistantSetup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài màn hình Desktop"; GroupDescription: "Shortcut bổ sung:"

[Files]
Source: "..\..\dist\MinAssistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở {#MyAppName}"; Flags: nowait postinstall skipifsilent

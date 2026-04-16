#define MyAppName "SoilSens Master"
#define MyAppVersion "3.7.9"
#define MyAppPublisher "MAT-Granichin-Lab"
#define MyAppExeName "SoilSensMaster.exe"
#define MyProfilesDir "{userappdata}\SoilSensorMonitor\profiles"
#define MyLogsDir "{userappdata}\SoilSensorMonitor\logs"

[Setup]
AppId={{2E967104-C10B-4CC1-B3D6-4E8E6FB3FE40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SoilSens Master
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=output
OutputBaseFilename=SoilSensMaster_Setup
SetupIconFile=..\\icon.ico
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{#MyProfilesDir}"; Permissions: users-modify
Name: "{#MyLogsDir}"; Permissions: users-modify

[Files]
Source: "..\\dist\\SoilSensMaster.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\\profiles\\*.json"; DestDir: "{#MyProfilesDir}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{autoprograms}\{#MyAppName} - Open Profiles Folder"; Filename: "{sys}\explorer.exe"; Parameters: """{#MyProfilesDir}"""
Name: "{autoprograms}\{#MyAppName} - Open Logs Folder"; Filename: "{sys}\explorer.exe"; Parameters: """{#MyLogsDir}"""
Name: "{autoprograms}\{#MyAppName} - Error Log Console"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoExit -Command ""New-Item -Path '{#MyLogsDir}\error.log' -ItemType File -Force | Out-Null; Get-Content -Path '{#MyLogsDir}\error.log' -Wait -Tail 40"""
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent


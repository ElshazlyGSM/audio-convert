[Setup]
AppId={{E9B8C2E5-0D99-4A2C-8A3E-6B5B8B5B9A41}
AppName=Song Cover Tool
AppVersion=1.0.0
AppPublisher=Song Cover Tool
DefaultDirName={autopf}\Song Cover Tool
DefaultGroupName=Song Cover Tool
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=SongCoverToolSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\SongCoverTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Song Cover Tool"; Filename: "{app}\SongCoverTool.exe"
Name: "{commondesktop}\Song Cover Tool"; Filename: "{app}\SongCoverTool.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\SongCoverTool.exe"; Description: "Launch Song Cover Tool"; Flags: nowait postinstall skipifsilent

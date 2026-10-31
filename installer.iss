[Setup]
AppId={{E9B8C2E5-0D99-4A2C-8A3E-6B5B8B5B9A41}
AppName=Media Audio Studio
AppVersion=1.0.0
AppPublisher=ahmed elshazly
AppPublisherURL=mailto:Elshazly.gsm@gmail.com
AppSupportURL=mailto:Elshazly.gsm@gmail.com
AppUpdatesURL=mailto:Elshazly.gsm@gmail.com
AppContact=Elshazly.gsm@gmail.com
DefaultDirName={autopf}\Media Audio Studio
DefaultGroupName=Media Audio Studio
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=MediaAudioStudioSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\MediaAudioStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Media Audio Studio"; Filename: "{app}\MediaAudioStudio.exe"
Name: "{commondesktop}\Media Audio Studio"; Filename: "{app}\MediaAudioStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\MediaAudioStudio.exe"; Description: "Launch Media Audio Studio"; Flags: nowait postinstall skipifsilent

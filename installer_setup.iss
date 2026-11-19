; Inno Setup Script for ClipCraft Studio Pro
; Developer: ahmed elshazly <Elshazly.gsm@gmail.com>

#define MyAppName "ClipCraft Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ahmed elshazly"
#define MyAppURL "mailto:Elshazly.gsm@gmail.com"
#define MyAppExeName "ClipCraftStudio.exe"

[Setup]
; Basic Application Identification
AppId={{C6287F63-0C82-4A73-983C-43F1E7BF92F8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments=ClipCraft Studio - Professional NLE Video Editing & Audio Engineering
AppContact=Elshazly.gsm@gmail.com

; PE File Version Information (Displays properly in Windows Explorer Properties instead of 0.0.0.0)
VersionInfoVersion=1.0.0.0
VersionInfoTextVersion=1.0.0
VersionInfoCompany=ahmed elshazly
VersionInfoDescription=ClipCraft Studio Setup Installer
VersionInfoCopyright=Copyright (C) 2026 ahmed elshazly <Elshazly.gsm@gmail.com>
VersionInfoProductName=ClipCraft Studio
VersionInfoProductVersion=1.0.0.0

; Windows Add or Remove Programs (Programs and Features) Settings & Icon
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} Pro

; Destination Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=setup_output
OutputBaseFilename=ClipCraft_Studio_Setup_v1.0
SetupIconFile=app_icon.ico
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
WizardStyle=modern

; Language selection dialog at startup
ShowLanguageDialog=yes

; User privileges (Installs for current user or all users without requiring admin prompt)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"; InfoBeforeFile: "installer_info_ar.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "installer_info_en.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\ClipCraftStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Program Files\VideoLAN\VLC\libvlc.dll"; DestDir: "{app}\vlc"; Flags: ignoreversion
Source: "C:\Program Files\VideoLAN\VLC\libvlccore.dll"; DestDir: "{app}\vlc"; Flags: ignoreversion
Source: "C:\Program Files\VideoLAN\VLC\plugins\*"; DestDir: "{app}\vlc\plugins"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

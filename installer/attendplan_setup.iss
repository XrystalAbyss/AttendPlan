; Inno Setup Script for AttendPlan Windows Desktop Application
; Produces a per-user, non-administrative Windows installer (.exe)

#define MyAppName "AttendPlan"
#define MyAppVersion "0.1.0-beta.7"
#define MyAppPublisher "AttendPlan Team"
#define MyAppURL "https://github.com/XrystalAbyss/AttendPlan"
#define MyAppExeName "AttendPlan.exe"
#define MySourceDir "..\dist\AttendPlan"

[Setup]
; Basic Application Info
AppId={{C6B5E87D-1F33-4D91-8846-9D923E2A3819}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Non-administrative user mode installation
PrivilegesRequired=lowest
DefaultDirName={userappdata}\AttendPlan\app
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=..\release-candidates
OutputBaseFilename=AttendPlan-{#MyAppVersion}-Setup
Compression=lzma2/max
SolidCompression=yes

; Visual & Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableWelcomePage=no

; Uninstaller configuration
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Distribute all files from dist\AttendPlan
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up runtime caches inside the application directory, but DO NOT delete user database in parent folder
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\{#MyAppExeName}"


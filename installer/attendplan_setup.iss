; Inno Setup Script for AttendPlan Windows Desktop Application
; Produces a per-user, non-administrative Windows installer (.exe)

#define MyAppName "AttendPlan"
#define MyAppVersion "0.1.0-beta.8"
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
AppMutex=AttendPlanDesktopAppMutex

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
; Distribute maintenance scripts
Source: "AttendPlan-Maintenance.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\scripts\AttendPlan-Maintenance.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\AttendPlan — Maintenance and Reset"; Filename: "{app}\AttendPlan-Maintenance.cmd"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up application directory files
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\{#MyAppExeName}"
Type: files; Name: "{app}\AttendPlan-Maintenance.cmd"
Type: files; Name: "{app}\AttendPlan-Maintenance.ps1"

[Code]
var
  KeepUserDataOnUninstall: Boolean;

function GetInstalledVersion(): String;
var
  VersionStr: String;
begin
  VersionStr := '';
  RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C6B5E87D-1F33-4D91-8846-9D923E2A3819}_is1', 'DisplayVersion', VersionStr);
  Result := VersionStr;
end;

function InitializeSetup(): Boolean;
var
  InstalledVer: String;
begin
  Result := True;
  InstalledVer := GetInstalledVersion();
  if InstalledVer <> '' then
  begin
    if InstalledVer = '{#MyAppVersion}' then
    begin
      MsgBox('AttendPlan version ' + InstalledVer + ' is already installed.' + #13#10 + #13#10 +
             'Setup will reinstall or repair the application files. Your saved attendance records and settings will be preserved.',
             mbInformation, MB_OK);
    end
    else if CompareText(InstalledVer, '{#MyAppVersion}') > 0 then
    begin
      if MsgBox('A newer version of AttendPlan (version ' + InstalledVer + ') is already installed.' + #13#10 + #13#10 +
                'Downgrading to version {#MyAppVersion} may cause incompatibilities with your saved attendance data.' + #13#10 + #13#10 +
                'Do you want to continue anyway?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end
    else
    begin
      MsgBox('Setup detected existing AttendPlan (version ' + InstalledVer + ').' + #13#10 + #13#10 +
             'Setup will upgrade your installation in-place to version {#MyAppVersion}. All your saved semesters, courses, and settings will be preserved.',
             mbInformation, MB_OK);
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  Answer: Integer;
begin
  Result := True;
  KeepUserDataOnUninstall := True;
  Answer := MsgBox('Do you want to keep your saved attendance records, course history, and settings?' + #13#10 + #13#10 +
                   'Click YES to keep your academic data for future reinstallation (Recommended).' + #13#10 + #13#10 +
                   'Click NO to permanently delete all local AttendPlan data.',
                   mbConfirmation, MB_YESNO);
  if Answer = IDNO then
  begin
    Answer := MsgBox('WARNING: This will permanently delete your attendance database and all saved history!' + #13#10 + #13#10 +
                     'Are you sure you want to permanently delete all local AttendPlan data?',
                     mbError, MB_YESNO);
    if Answer = IDYES then
    begin
      KeepUserDataOnUninstall := False;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if not KeepUserDataOnUninstall then
    begin
      DataDir := ExpandConstant('{localappdata}\AttendPlan');
      if (DataDir <> '') and DirExists(DataDir) and (Pos('AttendPlan', DataDir) > 0) then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;

; Inno Setup Script for AttendPlan Windows Desktop Application
; Produces a per-user, non-administrative Windows installer (.exe)

#define MyAppName "AttendPlan"
#define MyAppVersion "0.1.0-beta.9"
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
; Clean up application directory files in {app}
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\{#MyAppExeName}"
Type: files; Name: "{app}\AttendPlan-Maintenance.cmd"
Type: files; Name: "{app}\AttendPlan-Maintenance.ps1"

[Code]
function ParseLeadingNumber(S: String): Integer;
var
  I: Integer;
  NumStr: String;
begin
  NumStr := '';
  for I := 1 to Length(S) do
  begin
    if (S[I] >= '0') and (S[I] <= '9') then
      NumStr := NumStr + S[I]
    else if Length(NumStr) > 0 then
      Break;
  end;
  Result := StrToIntDef(NumStr, 0);
end;

function CompareSemanticVersions(V1, V2: String): Integer;
var
  Main1, Main2, Pre1, Pre2: String;
  HyphenPos: Integer;
  HasPre1, HasPre2: Boolean;
  DotPos: Integer;
  Major1, Minor1, Patch1: Integer;
  Major2, Minor2, Patch2: Integer;
  PreNum1, PreNum2: Integer;
  TagCmp: Integer;
  PreTag1, PreTag2: String;
begin
  // Split V1 on hyphen for prerelease
  HyphenPos := Pos('-', V1);
  if HyphenPos > 0 then
  begin
    Main1 := Copy(V1, 1, HyphenPos - 1);
    Pre1 := Copy(V1, HyphenPos + 1, Length(V1));
    HasPre1 := True;
  end
  else
  begin
    Main1 := V1;
    Pre1 := '';
    HasPre1 := False;
  end;

  // Split V2 on hyphen for prerelease
  HyphenPos := Pos('-', V2);
  if HyphenPos > 0 then
  begin
    Main2 := Copy(V2, 1, HyphenPos - 1);
    Pre2 := Copy(V2, HyphenPos + 1, Length(V2));
    HasPre2 := True;
  end
  else
  begin
    Main2 := V2;
    Pre2 := '';
    HasPre2 := False;
  end;

  // Parse Main1: Major.Minor.Patch
  DotPos := Pos('.', Main1);
  if DotPos > 0 then
  begin
    Major1 := StrToIntDef(Copy(Main1, 1, DotPos - 1), 0);
    Main1 := Copy(Main1, DotPos + 1, Length(Main1));
    DotPos := Pos('.', Main1);
    if DotPos > 0 then
    begin
      Minor1 := StrToIntDef(Copy(Main1, 1, DotPos - 1), 0);
      Patch1 := StrToIntDef(Copy(Main1, DotPos + 1, Length(Main1)), 0);
    end
    else
    begin
      Minor1 := StrToIntDef(Main1, 0);
      Patch1 := 0;
    end;
  end
  else
  begin
    Major1 := StrToIntDef(Main1, 0);
    Minor1 := 0;
    Patch1 := 0;
  end;

  // Parse Main2: Major.Minor.Patch
  DotPos := Pos('.', Main2);
  if DotPos > 0 then
  begin
    Major2 := StrToIntDef(Copy(Main2, 1, DotPos - 1), 0);
    Main2 := Copy(Main2, DotPos + 1, Length(Main2));
    DotPos := Pos('.', Main2);
    if DotPos > 0 then
    begin
      Minor2 := StrToIntDef(Copy(Main2, 1, DotPos - 1), 0);
      Patch2 := StrToIntDef(Copy(Main2, DotPos + 1, Length(Main2)), 0);
    end
    else
    begin
      Minor2 := StrToIntDef(Main2, 0);
      Patch2 := 0;
    end;
  end
  else
  begin
    Major2 := StrToIntDef(Main2, 0);
    Minor2 := 0;
    Patch2 := 0;
  end;

  // Compare Major, Minor, Patch
  if Major1 <> Major2 then
  begin
    Result := Major1 - Major2;
    Exit;
  end;
  if Minor1 <> Minor2 then
  begin
    Result := Minor1 - Minor2;
    Exit;
  end;
  if Patch1 <> Patch2 then
  begin
    Result := Patch1 - Patch2;
    Exit;
  end;

  // If Major.Minor.Patch identical: GA release without prerelease is NEWER than prerelease
  if HasPre1 and (not HasPre2) then
  begin
    Result := -1;
    Exit;
  end;
  if (not HasPre1) and HasPre2 then
  begin
    Result := 1;
    Exit;
  end;
  if (not HasPre1) and (not HasPre2) then
  begin
    Result := 0;
    Exit;
  end;

  // Both have prereleases, e.g. "beta.8" and "beta.10"
  DotPos := Pos('.', Pre1);
  if DotPos > 0 then
  begin
    PreTag1 := Copy(Pre1, 1, DotPos - 1);
    PreNum1 := StrToIntDef(Copy(Pre1, DotPos + 1, Length(Pre1)), 0);
  end
  else
  begin
    PreTag1 := Pre1;
    PreNum1 := ParseLeadingNumber(Pre1);
  end;

  DotPos := Pos('.', Pre2);
  if DotPos > 0 then
  begin
    PreTag2 := Copy(Pre2, 1, DotPos - 1);
    PreNum2 := StrToIntDef(Copy(Pre2, DotPos + 1, Length(Pre2)), 0);
  end
  else
  begin
    PreTag2 := Pre2;
    PreNum2 := ParseLeadingNumber(Pre2);
  end;

  TagCmp := CompareText(PreTag1, PreTag2);
  if TagCmp <> 0 then
  begin
    Result := TagCmp;
    Exit;
  end;

  Result := PreNum1 - PreNum2;
end;

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
  CmpRes: Integer;
begin
  Result := True;
  InstalledVer := GetInstalledVersion();
  if InstalledVer <> '' then
  begin
    CmpRes := CompareSemanticVersions(InstalledVer, '{#MyAppVersion}');
    if CmpRes = 0 then
    begin
      MsgBox('AttendPlan version ' + InstalledVer + ' is already installed.' + #13#10 + #13#10 +
             'Setup will reinstall or repair application binaries. Your saved attendance records, course history, and settings will be preserved.',
             mbInformation, MB_OK);
    end
    else if CmpRes > 0 then
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
begin
  Result := True;
  // Non-destructive default: inform user that data in AppData is preserved
  MsgBox('AttendPlan application files and shortcuts will be uninstalled.' + #13#10 + #13#10 +
         'Your saved attendance database, course history, settings, and backups will remain preserved in your user profile for future reinstallation.' + #13#10 + #13#10 +
         'To manage, back up, or reset your local data at any time, use the AttendPlan Maintenance and Reset utility.',
         mbInformation, MB_OK);
end;

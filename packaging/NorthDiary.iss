#define ProductName "NorthDiary"
#define ProductVersion "1.7.0"
[Setup]
AppId={{59AA019B-A598-4A0D-B146-B656B278C317}
AppName={#ProductName}
AppVersion={#ProductVersion}
AppVerName=NorthDiary v{#ProductVersion}
AppPublisher=NorthCape
AppPublisherURL=https://github.com/NorthCape3179/NorthDiary
AppSupportURL=https://github.com/NorthCape3179/NorthDiary
DefaultDirName={localappdata}\Programs\NorthDiary
DefaultGroupName=NorthDiary
InfoBeforeFile=..\licenses\README-OPEN-SOURCE.txt
DisableProgramGroupPage=yes
DisableDirPage=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\release
OutputBaseFilename=NorthDiary-Setup-v{#ProductVersion}
SetupIconFile=..\northdiary\resources\northdiary.ico
UninstallDisplayIcon={app}\NorthDiary.exe
UninstallDisplayName=NorthDiary
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.7.0.0
VersionInfoProductName=NorthDiary
VersionInfoDescription=NorthDiary 安装程序
VersionInfoCompany=NorthCape
VersionInfoCopyright=Copyright 2026 NorthCape

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "..\dist\NorthDiary\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\NorthDiary"; Filename: "{app}\NorthDiary.exe"; WorkingDir: "{app}"; IconFilename: "{app}\NorthDiary.exe"
Name: "{autodesktop}\NorthDiary"; Filename: "{app}\NorthDiary.exe"; WorkingDir: "{app}"; IconFilename: "{app}\NorthDiary.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NorthDiary.exe"; Description: "启动 NorthDiary"; Flags: nowait postinstall skipifsilent

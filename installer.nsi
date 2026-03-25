; Script for creating a Windows installer using NSIS

!include "LogicLib.nsh"
!include "MUI2.nsh"

OutFile "MyAppInstaller.exe"
InstallDir "$PROGRAMFILES\MyApp"

Section
    SetOutPath "$INSTDIR"
    File "myapp.exe"
    File "mylibrary.dll"
    File "README.txt"
SectionEnd

; Welcome pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Define the default section
!define MUI_DEFAULT_PAGE_STYLE modern

; Use the installer
Function .onInstSuccess
    MessageBox MB_OK "Installation Complete!"
FunctionEnd

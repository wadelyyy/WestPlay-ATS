; This fixture never installs WestPlay or touches real Desktop/Start-menu paths.
; Runtime files and shortcuts stay beside the generated test executable.
Unicode true
SilentInstall silent
RequestExecutionLevel user
!include MUI2.nsh
!include FileFunc.nsh
!include x64.nsh
!include WordFunc.nsh
!include "Win\COM.nsh"
!include "Win\Propkey.nsh"
!include "${ATS_NSIS_UTILS}"
!include "${__FILEDIR__}\ats-installer-hooks.nsh"

; Match Tauri's declaration order: hooks are included before these names exist.
!define PRODUCTNAME "ATS WestPlay"
!define MAINBINARYNAME "westplay"
!define STARTMENUFOLDER "ATS WestPlay"
Var AppStartMenuFolder

Name "ATS shortcut hook smoke check"
OutFile "${ATS_TEST_OUTPUT}"
!insertmacro MUI_LANGUAGE "English"

; Compile the hook's Tauri-variable expansion, but never execute this fixture:
; its paths are intentionally the real shell-folder variables in the source.
Function AtsCompilePostInstallFixture
  !insertmacro NSIS_HOOK_POSTINSTALL
FunctionEnd

Section
  StrCpy $AtsMainBinary "$EXEDIR\westplay.exe"
  StrCpy $AtsStartMenuShortcut "$EXEDIR\start-menu.lnk"
  StrCpy $AtsDesktopShortcut "$EXEDIR\desktop.lnk"
  FileOpen $9 "$AtsMainBinary" w
  FileWrite $9 "Not an executable. Shortcut target fixture only."
  FileClose $9
  CreateShortcut "$AtsStartMenuShortcut" "$AtsMainBinary" "--launch-ats"
  CreateShortcut "$AtsDesktopShortcut" "$AtsMainBinary" "--launch-ats"
  CreateShortcut "$EXEDIR\foreign.lnk" "$EXEDIR\another-app.exe" "--keep"
  StrCpy $AtsShortcutsReady 1
  Call AtsFinalizeShortcuts
  ; Tauri's GUI finish-page action creates a fresh desktop shortcut after POSTINSTALL.
  CreateShortcut "$AtsDesktopShortcut" "$AtsMainBinary"
  Call AtsFinalizeShortcuts
  ; The target guard must leave a shortcut to another application unchanged.
  !insertmacro ATS_SET_COMPANION_ARGUMENTS "$EXEDIR\foreign.lnk"
SectionEnd

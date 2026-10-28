; Retain upstream's WebView2 prerequisite check. Shortcuts open only WestPlay;
; the player starts ATS manually or uses the explicit launch button in the app.
; Tauri's hook is included before PRODUCTNAME/MAINBINARYNAME and AppStartMenuFolder
; are declared. Resolve those names in POSTINSTALL and store them for GUI shutdown.
!include "${__FILEDIR__}\..\app\installer\hooks.nsh"

Var AtsShortcutsReady
Var AtsMainBinary
Var AtsDesktopShortcut
Var AtsStartMenuShortcut

; Modify only a shortcut whose target is this installation's binary. Loading and
; saving the existing ShellLink preserves its icon, AppUserModelId and other data.
!macro ATS_SET_COMPANION_ARGUMENTS shortcut
  Push $0
  Push $1
  Push $2
  Push $3
  Push $4
  !insertmacro IsShortcutTarget "${shortcut}" "$AtsMainBinary"
  Pop $4
  ${If} $4 = 1
    !insertmacro ComHlpr_CreateInProcInstance ${CLSID_ShellLink} ${IID_IShellLink} r0 ""
    ${If} $0 P<> 0
      ${IUnknown::QueryInterface} $0 '("${IID_IPersistFile}",.r1)'
      ${If} $1 P<> 0
        ${IPersistFile::Load} $1 '("${shortcut}", ${STGM_READWRITE})'
        ${IShellLink::SetArguments} $0 '(w "")'
        ${IPersistFile::Save} $1 '("${shortcut}",1)'
        ${IUnknown::Release} $1 ""
      ${EndIf}
      ${IUnknown::Release} $0 ""
    ${EndIf}
  ${EndIf}
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
!macroend

Function AtsFinalizeShortcuts
  ${If} $AtsShortcutsReady = 1
    !insertmacro ATS_SET_COMPANION_ARGUMENTS "$AtsStartMenuShortcut"
    !insertmacro ATS_SET_COMPANION_ARGUMENTS "$AtsDesktopShortcut"
  ${EndIf}
FunctionEnd

!macro NSIS_HOOK_POSTINSTALL
  StrCpy $AtsMainBinary "$INSTDIR\${MAINBINARYNAME}.exe"
  StrCpy $AtsDesktopShortcut "$DESKTOP\${PRODUCTNAME}.lnk"
  !if "${STARTMENUFOLDER}" != ""
    StrCpy $AtsStartMenuShortcut "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
  !else
    StrCpy $AtsStartMenuShortcut "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !endif
  StrCpy $AtsShortcutsReady 1
  ; Handles the start menu plus desktop links created by silent/passive installs.
  Call AtsFinalizeShortcuts
!macroend

; In the interactive installer, Tauri creates the optional desktop shortcut on
; the finish page, after POSTINSTALL. Clear arguments after that final write too.
; An aborted installation has no Ready flag and leaves shortcuts untouched.
Function .onGUIEnd
  Call AtsFinalizeShortcuts
FunctionEnd

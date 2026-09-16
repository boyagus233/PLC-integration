Set oWS = WScript.CreateObject("WScript.Shell")
sDesk = oWS.SpecialFolders("Desktop")

Set fso = CreateObject("Scripting.FileSystemObject")
sScriptPath = WScript.ScriptFullName
sToolsDir = fso.GetParentFolderName(sScriptPath)
If LCase(fso.GetFileName(sToolsDir)) = "tools" Then
    sRootDir = fso.GetParentFolderName(sToolsDir)
Else
    sRootDir = sToolsDir
End If

' 1. Edit Config
Set oLink = oWS.CreateShortcut(sDesk & "\[Yuasa] 1. Edit Config.lnk")
oLink.TargetPath = sRootDir & "\tools\Edit_Config.bat"
oLink.WorkingDirectory = sRootDir
oLink.IconLocation = "shell32.dll,69"
oLink.Description = "Buka file config.ini di Notepad untuk mengubah setting"
oLink.Save

' 2. Restart Service
Set oLink = oWS.CreateShortcut(sDesk & "\[Yuasa] 2. Restart Service.lnk")
oLink.TargetPath = sRootDir & "\tools\Restart_Service.bat"
oLink.WorkingDirectory = sRootDir
oLink.IconLocation = "shell32.dll,238"
oLink.Description = "Restart YuasaScannerService agar konfigurasi baru aktif"
oLink.Save

' 3. Cek Status Service
Set oLink = oWS.CreateShortcut(sDesk & "\[Yuasa] 3. Cek Status Service.lnk")
oLink.TargetPath = sRootDir & "\tools\Status_Service.bat"
oLink.WorkingDirectory = sRootDir
oLink.IconLocation = "shell32.dll,221"
oLink.Description = "Cek status service dan lihat baris log terbaru"
oLink.Save

' 4. Uninstall Service
Set oLink = oWS.CreateShortcut(sDesk & "\[Yuasa] 4. Uninstall Service.lnk")
oLink.TargetPath = sRootDir & "\tools\Uninstall_Service.bat"
oLink.WorkingDirectory = sRootDir
oLink.IconLocation = "shell32.dll,131"
oLink.Description = "Copot YuasaScannerService dari Windows"
oLink.Save


CreateObject("Wscript.Shell").Run "bin\win\install.bat", 1, True

Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set oLink = oWS.CreateShortcut(scriptDir & "\Snipping Lens.lnk")
oLink.TargetPath = scriptDir & "\bin\win\run.vbs"
oLink.IconLocation = scriptDir & "\bin\win\assets\sniplens.ico"
oLink.Save

oWS.Run Chr(34) & scriptDir & "\Snipping Lens.lnk" & Chr(34), 1, False

MsgBox "Installation complete. Snipping Lens 3 is now running in the taskbar.", vbInformation, "Snipping Lens 3 Setup"
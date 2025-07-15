CreateObject("Wscript.Shell").Run "bin\win\install.bat", 1, True

Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
oWS.Run Chr(34) & fso.BuildPath(scriptDir, "create_lnk.vbs") & Chr(34), 1, True

oWS.Run Chr(34) & scriptDir & "\Snipping Lens.lnk" & Chr(34), 1, False

MsgBox "Installation complete. Snipping Lens 3 is now running in the taskbar.", vbInformation, "Snipping Lens 3 Setup"
Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

oWS.Run Chr(34) & fso.BuildPath(scriptDir, "bin\win\install.bat") & Chr(34), 1, True
oWS.Run Chr(34) & fso.BuildPath(scriptDir, "bin\win\run.vbs") & Chr(34), 0, False

MsgBox "Installation complete. Snipping Lens 5 is now running in the taskbar.", vbInformation, "Snipping Lens 5 Setup"

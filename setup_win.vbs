CreateObject("Wscript.Shell").Run "bin\win\src\install.bat", 1, True

Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set oLink = oWS.CreateShortcut(scriptDir & "\Snipping Lens.lnk")
oLink.TargetPath = scriptDir & "\bin\win\src\run.vbs"
oLink.IconLocation = scriptDir & "\bin\win\src\sniplens.ico"
oLink.Save
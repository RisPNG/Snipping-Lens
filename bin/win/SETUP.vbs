CreateObject("Wscript.Shell").Run "src\install.bat", 1, True

Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set oLink = oWS.CreateShortcut(scriptDir & "\Snipping Lens.lnk")
oLink.TargetPath = scriptDir & "\src\run.vbs"
oLink.IconLocation = scriptDir & "\src\sniplens.ico"
oLink.Save
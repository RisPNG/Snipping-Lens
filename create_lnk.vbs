Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set oLink = oWS.CreateShortcut(scriptDir & "\Snipping Lens.lnk")
oLink.TargetPath = scriptDir & "\bin\win\run.vbs"
oLink.IconLocation = scriptDir & "\bin\win\assets\sniplens.ico"
oLink.Save
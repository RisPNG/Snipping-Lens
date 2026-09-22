Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

oWS.Run Chr(34) & fso.BuildPath(scriptDir, "bin\win\install.bat") & Chr(34), 1, True
oWS.Run Chr(34) & fso.BuildPath(scriptDir, "int\win\venv\Scripts\pythonw.exe") & Chr(34) & " " & Chr(34) & fso.BuildPath(scriptDir, "src\main.py") & Chr(34), 1, False

MsgBox "Installation complete. Snipping Lens 5 is now running in the taskbar.", vbInformation, "Snipping Lens 5 Setup"

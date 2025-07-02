Set objShell = CreateObject("Wscript.Shell")
objShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.Run "install.bat", 0, True
objShell.Run "launch.bat", 0, False
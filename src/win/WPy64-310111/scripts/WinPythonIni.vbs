
Set colArgs = WScript.Arguments
If colArgs.Count> 0 Then 
  Filename=colArgs(0) 
else 
  Filename="..\settings\winpython.ini"
end if
my_lines = Split(GetFile(FileName) & vbNewLine , vbNewLine )
segment = "environment"
txt=""
Set objWSH =  CreateObject("WScript.Shell")
For each l in my_lines
    if left(l, 1)="[" then
        segment=split(mid(l, 2, 999) & "]","]")(0)
    ElseIf left(l, 1) <> "#" and instr(l, "=")>0  then
        data = Split(l & "=", "=")
        if segment="debug" and trim(data(0))="state" then data(0)= "WINPYDEBUG"
        if segment="environment" or segment= "debug" then 
            txt= txt & "set " & rtrim(data(0)) & "=" & translate(ltrim(data(1))) & "&& "
            objWSH.Environment("PROCESS").Item(rtrim(data(0))) = translate(ltrim(data(1)))
        end if
        if segment="debug" and trim(data(0))="state" then txt= txt & "set WINPYDEBUG=" & trim(data(1)) & "&&"
    End If
Next
wscript.echo txt


Function GetFile(ByVal FileName)
    Set FS = CreateObject("Scripting.FileSystemObject")
    If Left(FileName,3)="..\" then FileName = FS.GetParentFolderName(FS.GetParentFolderName(Wscript.ScriptFullName)) & mid(FileName,3,9999)
    If Left(FileName,3)=".\" then FileName = FS.GetParentFolderName(FS.GetParentFolderName(Wscript.ScriptFullName)) & mid(FileName,3,9999)
    On Error Resume Next
    GetFile = FS.OpenTextFile(FileName).ReadAll
End Function

Function translate(line)
    set dos = objWSH.Environment("PROCESS")
    tab = Split(line & "%", "%")
    for i = 1 to Ubound(tab) step 2   
       if tab(i)& "" <> "" and dos.Item(tab(i)) & "" <> "" then tab(i) =  dos.Item(tab(i))
    next
    translate =  Join(tab, "") 
end function
        
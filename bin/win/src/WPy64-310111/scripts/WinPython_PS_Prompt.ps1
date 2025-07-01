
###############################
### WinPython_PS_Prompt.ps1 ###
###############################
$0 = $myInvocation.MyCommand.Definition
$dp0 = [System.IO.Path]::GetDirectoryName($0)

$env:WINPYDIRBASE = "$dp0\.."
# get a normalize path
# http://stackoverflow.com/questions/1645843/resolve-absolute-path-from-relative-path-and-or-file-name
$env:WINPYDIRBASE = [System.IO.Path]::GetFullPath( $env:WINPYDIRBASE )

# avoid double_init (will only resize screen)
if (-not ($env:WINPYDIR -eq [System.IO.Path]::GetFullPath( $env:WINPYDIRBASE+"\python-3.10.11.amd64")) ) {


$env:WINPYDIR = $env:WINPYDIRBASE+"\python-3.10.11.amd64"
# 2019-08-25 pyjulia needs absolutely a variable PYTHON=%WINPYDIR%python.exe
$env:PYTHON = "%WINPYDIR%\python.exe"


$env:WINPYVER = '3.10.11.1'
# rem 2023-02-12 try utf-8 on console
# rem see https://github.com/pypa/pip/issues/11798#issuecomment-1427069681
$env:PYTHONIOENCODING = "utf-8"

$env:HOME = "$env:WINPYDIRBASE\settings"

# rem read https://github.com/winpython/winpython/issues/839
# $env:USERPROFILE = "$env:HOME"

$env:WINPYDIRBASE = ""
$env:JUPYTER_DATA_DIR = "$env:HOME"
$env:WINPYARCH = 'WIN32'
if ($env:WINPYARCH.subString($env:WINPYARCH.length-5, 5) -eq 'amd64')  {
   $env:WINPYARCH = 'WIN-AMD64' } 


if (-not $env:PATH.ToLower().Contains(";"+ $env:WINPYDIR.ToLower()+ ";"))  {
 $env:PATH = "$env:WINPYDIR\Lib\site-packages\PyQt5;$env:WINPYDIR\Lib\site-packages\PySide2;$env:WINPYDIR\;$env:WINPYDIR\DLLs;$env:WINPYDIR\Scripts;$env:WINPYDIR\..\t;$env:WINPYDIR\..\t\Julia\bin;$env:WINPYDIR\..\n;$env:path;" }

#rem force default pyqt5 kit for Spyder if PyQt5 module is there
if (Test-Path "$env:WINPYDIR\Lib\site-packages\PyQt5\__init__.py") { $env:QT_API = "pyqt5" } 



#####################
### handle R if included
#####################
if (Test-Path "$env:WINPYDIR\..\t\R\bin") { 
    $env:R_HOME = "$env:WINPYDIR\..\t\R"
    $env:R_HOMEbin = "$env:R_HOME\bin\x64"
    if ("$env:WINPYARCH" -eq "WIN32") {
        $env:R_HOMEbin = "$env:R_HOME\bin\i386"
    }
}

#####################
### handle Julia if included
#####################
if (Test-Path "$env:WINPYDIR\..\t\Julia\bin") {
    $env:JULIA_HOME = "$env:WINPYDIR\..\t\Julia\bin\"
    $env:JULIA_EXE = "julia.exe"
    $env:JULIA = "$env:JULIA_HOME$env:JULIA_EXE"
    $env:JULIA_PKGDIR = "$env:WINPYDIR\..\settings\.julia"
}

#####################
### handle PySide2 if included
#####################

$env:tmp_pyz = "$env:WINPYDIR\Lib\site-packages\PySide2"
if (Test-Path "$env:tmp_pyz") {
   $env:tmp_pyz = "$env:tmp_pyz\qt.conf"
   if (-not (Test-Path "$env:tmp_pyz")) {
      "[Paths]"| Add-Content -Path $env:tmp_pyz
      "Prefix = ."| Add-Content -Path $env:tmp_pyz
      "Binaries = ."| Add-Content -Path $env:tmp_pyz
   }
}

#####################
### handle PyQt5 if included
#####################
$env:tmp_pyz = "$env:WINPYDIR\Lib\site-packages\PyQt5"
if (Test-Path "$env:tmp_pyz") {
   $env:tmp_pyz = "$env:tmp_pyz\qt.conf"
   if (-not (Test-Path "$env:tmp_pyz")) {
      "[Paths]"| Add-Content -Path $env:tmp_pyz
      "Prefix = ."| Add-Content -Path $env:tmp_pyz
      "Binaries = ."| Add-Content -Path $env:tmp_pyz
   }
}


#####################
### handle pyqt5_tools if included
#####################
$env:tmp_pyz = "$env:WINPYDIR\Lib\site-packages\pyqt5_tools"
if (Test-Path "$env:tmp_pyz") {
   $env:QT_PLUGIN_PATH = "WINPYDIR\Lib\site-packages\pyqt5_tools\Qt\plugins"
}


#####################
### handle Pyzo configuration part
#####################
$env:tmp_pyz = "$env:HOME\.pyzo"
if (-not (Test-Path "$env:tmp_pyz")) { md -Path "$env:tmp_pyz" }
$env:tmp_pyz = "$env:HOME\.pyzo\config.ssdf"
if (-not (Test-Path "$env:tmp_pyz")) {
shellConfigs2 = list:| Add-Content -Path $env:tmp_pyz
 dict:| Add-Content -Path $env:tmp_pyz
   name = 'Python'| Add-Content -Path $env:tmp_pyz
   exe = '.\\python.exe'| Add-Content -Path $env:tmp_pyz
   ipython = 'no'| Add-Content -Path $env:tmp_pyz
   gui = 'none'| Add-Content -Path $env:tmp_pyz
}


#####################
### WinPython.ini part (removed from nsis)
#####################
if (-not (Test-Path "$env:WINPYDIR\..\settings")) { md -Path "$env:WINPYDIR\..\settings" }
if (-not (Test-Path "$env:WINPYDIR\..\settings\AppData")) { md -Path "$env:WINPYDIR\..\settings\AppData" }
if (-not (Test-Path "$env:WINPYDIR\..\settings\AppData\Roaming")) { md -Path "$env:WINPYDIR\..\settings\AppData\Roaming" }
$env:winpython_ini = "$env:WINPYDIR\..\settings\winpython.ini"
if (-not (Test-Path $env:winpython_ini)) {
    "[debug]" | Add-Content -Path $env:winpython_ini
    "state = disabled" | Add-Content -Path $env:winpython_ini
    "[environment]" | Add-Content -Path $env:winpython_ini
    "## <?> Uncomment lines to override environment variables" | Add-Content -Path $env:winpython_ini
    "#HOME = %%HOMEDRIVE%%%%HOMEPATH%%\Documents\WinPython%%WINPYVER%%" | Add-Content -Path $env:winpython_ini
    "#USERPROFILE = %%HOME%%" | Add-Content -Path $env:winpython_ini
    "#JUPYTER_DATA_DIR = %%HOME%%" | Add-Content -Path $env:winpython_ini
    "#JUPYTERLAB_SETTINGS_DIR = %%HOME%%\.jupyter\lab" | Add-Content -Path $env:winpython_ini
    "#JUPYTERLAB_WORKSPACES_DIR = %%HOME%%\.jupyter\lab\workspaces" | Add-Content -Path $env:winpython_ini
    "#WINPYWORKDIR = %%HOMEDRIVE%%%%HOMEPATH%%\Documents\WinPython%%WINPYVER%%\Notebooks" | Add-Content -Path $env:winpython_ini
}


} 
###############################
### Set-WindowSize
###############################
Function Set-WindowSize {
Param([int]$x=$host.ui.rawui.windowsize.width,
      [int]$y=$host.ui.rawui.windowsize.heigth,
      [int]$buffer=$host.UI.RawUI.BufferSize.heigth)
    
    $buffersize = new-object System.Management.Automation.Host.Size($x,$buffer)
    $host.UI.RawUI.BufferSize = $buffersize
    $size = New-Object System.Management.Automation.Host.Size($x,$y)
    $host.ui.rawui.WindowSize = $size   
}
# Windows10 yelling at us with 150 40 6000
# no more needed ?
# Set-WindowSize 195 40 6000 

### Colorize to distinguish
#$host.ui.RawUI.BackgroundColor = "DarkBlue"
$host.ui.RawUI.BackgroundColor = "Black"
$host.ui.RawUI.ForegroundColor = "White"


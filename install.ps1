# Registers the ASCII wallpaper to start when you log in, and starts it now.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = & python -c "import sys; print(sys.executable)"
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { throw "pythonw.exe not found next to $py" }
$script = Join-Path $here 'ascii_wallpaper.pyw'

$cmd = "`"$pyw`" `"$script`""
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'AsciiWallpaper' -Value $cmd
Write-Host "Startup entry added: $cmd"

Start-Process -FilePath $pyw -ArgumentList "`"$script`"" -WorkingDirectory $here
Write-Host "ASCII wallpaper started."

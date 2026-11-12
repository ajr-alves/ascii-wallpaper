# Sets the ASCII wallpaper to start when you log in, and starts it now.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = & python -c "import sys; print(sys.executable)"
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { throw "pythonw.exe not found next to $py" }
$script = Join-Path $here 'ascii_wallpaper.pyw'

# creates a Task Scheduler logon task (falls back to the registry Run key)
& python $script --startup on

Start-Process -FilePath $pyw -ArgumentList "`"$script`"" -WorkingDirectory $here
Write-Host "ASCII wallpaper started."

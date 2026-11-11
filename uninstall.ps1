# Removes the startup entry and stops the running wallpaper.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'AsciiWallpaper' -ErrorAction SilentlyContinue
& python (Join-Path $here 'ascii_wallpaper.pyw') --stop
Write-Host "ASCII wallpaper stopped and removed from startup."

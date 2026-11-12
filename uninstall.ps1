# Removes the wallpaper from startup and stops it.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here 'ascii_wallpaper.pyw'
& python $script --startup off
& python $script --stop
Write-Host "ASCII wallpaper stopped and removed from startup."

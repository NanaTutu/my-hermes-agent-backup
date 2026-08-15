param([string]$Src, [string]$Out, [int]$X, [int]$Y, [int]$W, [int]$H)
# Crop a full-screen PNG to a window rect so vision_analyze sees one clean
# window (a cluttered desktop makes the vision model hallucinate positions).
# X/Y/W/H = GetWindowRect L/T and width/height in physical px.
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Image]::FromFile($Src)
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.DrawImage($src, (New-Object System.Drawing.Rectangle 0,0,$W,$H), (New-Object System.Drawing.Rectangle $X,$Y,$W,$H), [System.Drawing.GraphicsUnit]::Pixel)
$bmp.Save($Out)
$g.Dispose(); $bmp.Dispose(); $src.Dispose()
Write-Output "cropped -> $Out"

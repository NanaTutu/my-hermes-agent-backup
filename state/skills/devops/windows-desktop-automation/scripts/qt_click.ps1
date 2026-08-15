param([int]$X, [int]$Y)
# Left-click at SCREEN coordinates (physical px) via Win32.
# Moves the REAL cursor and clicks (foreground input). Run after qt_raise.ps1
# so the target window is on top at those coordinates.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Click {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
}
"@
[Click]::SetCursorPos($X, $Y) | Out-Null
Start-Sleep -Milliseconds 120
[Click]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)  # LEFTDOWN
Start-Sleep -Milliseconds 60
[Click]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)  # LEFTUP
Write-Output "clicked at ($X, $Y)"

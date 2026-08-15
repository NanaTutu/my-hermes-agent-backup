param([string]$ProcessName = "CapCut")
# Bring a native Qt/custom-rendered app window to the foreground.
# Works even when cua-driver's session is dead. Uses the Alt-key
# foreground-lock release trick before SetForegroundWindow.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Raise {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    const byte VK_MENU = 0x12;
    const int SW_RESTORE = 9;
    public static void Bring(IntPtr h) {
        if (IsIconic(h)) ShowWindow(h, SW_RESTORE);
        keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
        keybd_event(VK_MENU, 0, 2, UIntPtr.Zero);
        SetForegroundWindow(h);
        ShowWindow(h, SW_RESTORE);
    }
}
"@
$p = Get-Process $ProcessName -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
if (-not $p) { Write-Output "NO WINDOW for $ProcessName"; exit 1 }
[Raise]::Bring($p.MainWindowHandle)
Start-Sleep -Milliseconds 400
[Raise]::SetForegroundWindow($p.MainWindowHandle)
Write-Output "raised pid=$($p.Id) title='$($p.MainWindowTitle)' hwnd=$($p.MainWindowHandle)"

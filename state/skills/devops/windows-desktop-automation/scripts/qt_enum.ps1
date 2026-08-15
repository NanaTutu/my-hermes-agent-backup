# Enumerate every visible top-level window (class | pid | title | WxH @ L,T).
# Use to diagnose a cluttered desktop: which windows cover your target and
# where the target actually sits before you click.
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;
public class WinEnum {
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L; public int T; public int R; public int B; }
    delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    public static List<string> List() {
        var out_ = new List<string>();
        EnumWindows((h, l) => {
            if (!IsWindowVisible(h)) return true;
            var t = new StringBuilder(256); GetWindowText(h, t, 256);
            var c = new StringBuilder(256); GetClassName(h, c, 256);
            uint pid; GetWindowThreadProcessId(h, out pid);
            RECT r; GetWindowRect(h, out r);
            int w = r.R - r.L, ht = r.B - r.T;
            if (w > 50 && ht > 50) {
                out_.Add(string.Format("{0} | pid={1} | '{2}' | {3}x{4} @({5},{6})", c, pid, t, w, ht, r.L, r.T));
            }
            return true;
        }, IntPtr.Zero);
        return out_;
    }
}
"@
[WinEnum]::List() | ForEach-Object { $_ }

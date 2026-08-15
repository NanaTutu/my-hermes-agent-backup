# Qt / native-app pixel path (CapCut worked example)

## Symptom
`computer_use(action="capture", app="CapCut")` →
`capture failed: cua-driver get_window_state failed: ... UIA provider
unresponsive on hwnd 0x30830, class 'Qt622QWindowIcon'`.
CapCut 9.x is a Qt 6.2 app; its UIA bridge does not respond, so the SOM /
element path is unavailable. Drive it by pixel coordinates instead.

## Get the window rect (physical px) — write a .ps1, run with -File
```powershell
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L; public int T; public int R; public int B; }
}
"@
Get-Process <AppName> -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle } | ForEach-Object {
    $r = New-Object Win32+RECT
    [Win32]::GetWindowRect($_.MainWindowHandle, [ref]$r) | Out-Null
    "{0} | '{1}' | L{2} T{3} R{4} B{5} | visible={6}" -f $_.Id, $_.MainWindowTitle, $r.L, $r.T, $r.R, $r.B, [Win32]::IsWindowVisible($_.MainWindowHandle)
}
```
Run: `powershell -NoProfile -ExecutionPolicy Bypass -File winrect.ps1`
CapCut example output: `121564 | 'CapCut' | L560 T61 R2000 B1021 | visible=True`
(1440x960 window). Note: inline `Add-Type @"..."@` in a git-bash `-Command`
string throws "No characters are allowed after a here-string header" — always
`write_file` a `.ps1` and run with `-File`.

## See the window without UIA
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/screen_capture.ps1 shot.png`
then `vision_analyze(image_url="C:\Users\<u>\shot.png")`. Confirmed it reads the
CapCut home screen (Create project / Templates / Sign in / Join Pro / Downloads /
Library) with zero UIA involvement. Delete the transient PNG afterwards.

## Launch quirk (CapCut on an Intel-UHD-only host)
- Direct bash spawn (`cd Apps/9.x && ./CapCut.exe`) → logs
  `GPDevice::initEGLLibraryWithPath, FAILED to load EGL library!` then the
  process exits; only `VEDetector.exe` (crash detector) stays alive, so
  `tasklist | grep -i capcut` still matches but there is no main window.
- `explorer.exe "C:\Users\<u>\AppData\Local\CapCut\Apps\CapCut.exe"` → clean
  start: six `CapCut.exe` processes, main one ~570 MB, window appears.
- Lesson: GUI apps that init GPU/EGL should be launched through the shell, not
  spawned directly from git-bash.

## Install layout (per-user, no admin)
- `C:\Users\<u>\AppData\Local\CapCut\Apps\<ver>\CapCut.exe` (versioned, e.g.
  9.2.0.3931) + a versionless launcher stub at `...\Apps\CapCut.exe`.
- `cmd //c start "" "<path>"` from git-bash also works but opens a stray cmd
  window; `explorer.exe "<path>"` is cleaner.

## Full end-to-end loop (proven: CapCut "Create project" click)

Order matters; each step is a `scripts/` helper run with `-File`. This is pure
Win32 — it works even when the cua-driver session is dead.

1. **Raise the window.** It is usually buried under terminals/Explorer on a
   busy desktop, and its center (where the primary button often sits) gets
   covered. `scripts/qt_raise.ps1 -ProcessName CapCut` (SetForegroundWindow +
   Alt-key foreground-lock release, plus SW_RESTORE if minimized).
2. **Screenshot, then crop to the rect.**
   `scripts/screen_capture.ps1 shot.png` then
   `scripts/qt_crop.ps1 -Src shot.png -Out win.png -X 560 -Y 61 -W 1440 -H 960`.
   Cropping is essential: a full-screen image with overlapping windows makes
   the vision model fabricate window positions; the crop gives it one clean
   window.
3. **Locate the button** with `vision_analyze(win.png)` — ask for the button's
   center *in the cropped image*. Map to screen coords: screen = rect origin +
   in-image coord. (CapCut example: "Create project" at image (607,117) in a
   window at rect (560,61) → screen (1167,178).)
4. **Click** `scripts/qt_click.ps1 -X 1167 -Y 178` (SetCursorPos + `mouse_event`
   LEFTDOWN/LEFTUP). This moves the real cursor — foreground, not background —
   which is fine for a task the user explicitly asked you to drive.
5. **Verify** by re-running screenshot + crop + vision before doing anything
   else. (CapCut: home screen → editor with timeline/preview/properties panel
   confirmed the click landed.)

## CapCut UI notes (9.2.0.3931, home screen)

- "Create project" is NOT a center button in current builds — it sits in the
  top hero banner. Left sidebar: Home / Templates / Create with AI (Video
  Studio, Design Studio) / Spaces; profile block with "Join Pro" / "Create with
  Teams". Top-right can show a dismissible "Billing receipts" tooltip overlay
  (a "Got it" button) that may cover the top-right region.
- Single `Qt622QWindowIcon` toplevel (1440x960 on a 2560x1080 display in the
  worked example). Coordinates are tied to the rect — re-fetch the rect and
  re-locate the button if the window is moved or resized.

## Diagnosing a cluttered desktop

`scripts/qt_enum.ps1` lists every visible top-level window (class | pid | title
| WxH @ L,T) via EnumWindows. Use it to see which windows cover your target and
where it actually sits before clicking. CapCut example: a
`ConsoleWindowClass 'Command Prompt - hermes'` and a `CabinetWClass` Explorer
window overlapped the editor's center, which is why a raw full-screen
`vision_analyze` misidentified the layout.

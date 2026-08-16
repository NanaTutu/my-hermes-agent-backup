# Headless subprocesses & respawning-process diagnosis (Windows)

Verified 2026-08-16 while fixing the hermesUI wrapper
(C:\Users\bohen\hermesUI\server.py) that kept popping a `hermes serve`
terminal every time it was closed.

## 1. The flag gotcha (proven matrix)

Goal: spawn a console app (`hermes serve`, `python server.py`, `node`) as a
subprocess with NO visible terminal window.

Empirical test — the child reports its own console-window handle via
GetConsoleWindow() (0 = no console = no visible terminal):

```python
import subprocess, sys
child = "import ctypes;print('console_hwnd=%d'%ctypes.windll.kernel32.GetConsoleWindow())"
def test(name, flags):
    p = subprocess.Popen([sys.executable, "-c", child],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=flags)
    out, _ = p.communicate(timeout=20)
    print(name, "->", out.decode().strip())

test("DETACHED only",            subprocess.DETACHED_PROCESS)
test("DETACHED|NEW_GROUP",       subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
test("DETACHED|NEW_GROUP|NO_WINDOW", subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
test("NEW_GROUP|NO_WINDOW",      subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
test("NO_WINDOW only",           subprocess.CREATE_NO_WINDOW)
```

Result on cpython 3.11 (this host):
- DETACHED_PROCESS only          -> console_hwnd != 0  (window appears)
- DETACHED|NEW_GROUP             -> console_hwnd != 0  (window appears)
- DETACHED|NEW_GROUP|NO_WINDOW   -> console_hwnd != 0  (CREATE_NO_WINDOW IGNORED)
- NEW_GROUP|NO_WINDOW            -> console_hwnd == 0  (no window)   <-- use this
- NO_WINDOW only                 -> console_hwnd == 0  (no window)

Why: (a) Microsoft documents CREATE_NO_WINDOW as ignored when combined with
DETACHED_PROCESS or CREATE_NEW_CONSOLE; (b) CPython 3.11 only maps
CREATE_NO_WINDOW -> STARTF_USESHOWWINDOW/SW_HIDE when `shell=True`. So
DETACHED_PROCESS must be DROPPED, not supplemented.

Correct launch flags for a headless server child:

```python
kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
# plus stdin=subprocess.DEVNULL and stdout/stderr -> a log file
```

## 2. Finding what keeps relaunching a process

A window that respawns after you close it = an autostart entry + a watchdog
loop, not a crash. Parent-PID analysis (run from git-bash):

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match '<needle>' } | Select ProcessId,ParentProcessId,Name,CreationDate,CommandLine | Format-List"
```

The process whose PID equals the offender's `ParentProcessId` is the spawner.
A `pythonw.exe`/`python.exe` wrapper running `<wrapper>/server.py` with a
`while True: sleep(30); restart-if-down` watchdog thread is the usual culprit.

Autostart homes to check (all three):

```bash
# Startup folders (user + common)
ls -la "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup"
ls -la "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp"
# Registry Run keys
reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
reg query "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"
# Scheduled tasks
schtasks //query //fo LIST //v | grep -i <needle>
```

Read a .lnk's target without opening it:

```bash
powershell -NoProfile -Command "\$s=(New-Object -ComObject WScript.Shell).CreateShortcut('C:\\path\\to\\x.lnk'); \$s.TargetPath; \$s.Arguments; \$s.WorkingDirectory"
```

## 3. Kill order + clean detached relaunch

1. Kill the WRAPPER tree first — its watchdog dies with it, so it cannot
   respawn the child: `taskkill /PID <wrapper_pid> /T /F`.
2. Then kill the child tree if anything is left.
3. Relaunch the wrapper detached and headless:

```bash
powershell -NoProfile -Command "Start-Process -FilePath 'C:\\...\\pythonw.exe' -ArgumentList 'C:\\...\\server.py','--no-open' -WorkingDirectory 'C:\\...' -WindowStyle Hidden"
```

Start-Process fully detaches from the calling shell; a `terminal`-background
`pythonw` spawn can be tied to that shell's lifecycle instead.

## 4. Orchestration pitfalls (hit live this session)

- Inline orchestrating in a bash heredoc: `\U`-style backslash paths in Python
  string literals raise `SyntaxError: unicodeescape ... truncated \UXXXXXXXX
  escape`. Use raw strings (`r"C:\..."`) or better, write the script to a file
  with `write_file` (raw-string paths) and run it.
- Passing an MSYS `/c/Users/...` path as an argument to native `python`
  double-converts to `C:\c\Users\...` and the script is "not found". Pass a
  native `C:/Users/...` path instead (see SKILL.md pitfall #2).

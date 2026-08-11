#!/usr/bin/env powershell
# get_default_audio.ps1 — OS-truth default audio endpoints via Core Audio API.
# sounddevice's query_devices() reflects host-API defaults, which can drift
# (e.g. Iriun webcam mics grabbing the default role when their app runs).
# This reads the actual Windows default via IMMDeviceEnumerator.
#
# Usage (from bash):  powershell -NoProfile -ExecutionPolicy Bypass -File get_default_audio.ps1
# Checks: CAPTURE (input) and RENDER (output) for the Console and
# Communications roles. Expect the Realtek Array for capture on this rig.

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject { }
[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator { int EnumAudioEndpoints(int ff, int ss, out IntPtr p); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice d); }
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice { int Activate(ref Guid i, int c, IntPtr p, out IntPtr o); int OpenPropertyStore(int s, out IPropertyStore st); int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id); int GetState(out int s); }
[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPropertyStore { int GetCount(out int c); int GetAt(int i, out IntPtr k); int GetValue(ref PropertyKey k, out PropVariant v); int SetValue(ref PropertyKey k, ref PropVariant v); int Commit(); }
[StructLayout(LayoutKind.Sequential)] struct PropertyKey { public Guid fmtid; public int pid; }
[StructLayout(LayoutKind.Explicit)] struct PropVariant { [FieldOffset(0)] public short vt; [FieldOffset(8)] public IntPtr ptr; }
public class AudioDef {
  public static string GetDefault(int dataFlow, string roleName) {
    var e = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
    IMMDevice d; int hr = e.GetDefaultAudioEndpoint(dataFlow, 0, out d);
    if (hr != 0) return roleName + ": HRESULT 0x" + hr.ToString("X8");
    string id; d.GetId(out id);
    IPropertyStore st; d.OpenPropertyStore(0, out st);
    PropertyKey k = new PropertyKey(); k.fmtid = new Guid("{A45C254E-DF1C-4EFD-8020-67D146A850E0}"); k.pid = 14;
    PropVariant v; st.GetValue(ref k, out v);
    return roleName + ": " + Marshal.PtrToStringUni(v.ptr) + "  [" + id + "]";
  }
}
'@
[AudioDef]::GetDefault(1, 'CAPTURE-Console')
[AudioDef]::GetDefault(1, 'CAPTURE-Comm')
[AudioDef]::GetDefault(0, 'RENDER-Console')